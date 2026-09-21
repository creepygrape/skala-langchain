from __future__ import annotations

from typing import Any

import pytest
from langchain_core.documents import Document

from app.extractors import OcrProcessingError
from app.loaders import NolTicketPage
from app.models import TicketGuideResponse
from app.rag import QueryAnalysis
from app.services import TicketGuideService


class FakeLoader:
    def __init__(self) -> None:
        self.loaded_urls: list[str] = []
        self.image_urls = ("https://example.com/notice.jpg",)

    def extract_concert_id(self, url: str) -> str:
        return url.rsplit("/", 1)[-1]

    def load(self, url: str) -> NolTicketPage:
        self.loaded_urls.append(url)
        return NolTicketPage(
            concert_id="26012624",
            source_url=url,
            text="공연 HTML 안내",
            image_urls=self.image_urls,
        )


class FakeExtractor:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.error: Exception | None = None

    def extract(self, image_url: str) -> str:
        self.urls.append(image_url)
        if self.error is not None:
            raise self.error
        return "상세 이미지 OCR 안내"


class FakeProcessor:
    def __init__(self) -> None:
        self.built_with: tuple[Any, Any] | None = None
        self.split_input: Any = None
        self.documents = [Document(page_content="통합 문서")]
        self.chunks = [Document(page_content="검색 Chunk")]

    def build_documents(self, page: Any, image_texts: Any) -> list[Document]:
        self.built_with = (page, image_texts)
        return self.documents

    def split_documents(self, documents: Any) -> list[Document]:
        self.split_input = documents
        return self.chunks


class FakeVectorStore:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.index_calls: list[tuple[str, Any]] = []
        self.retrieve_calls: list[tuple[str, str]] = []
        self.results = [Document(page_content="관련 검색 결과")]

    def has_concert(self, concert_id: str) -> bool:
        return self.exists

    def index_documents(self, concert_id: str, chunks: Any) -> bool:
        self.index_calls.append((concert_id, chunks))
        self.exists = True
        return True

    def retrieve(self, concert_id: str, query: str) -> list[Document]:
        self.retrieve_calls.append((concert_id, query))
        return self.results


class FakeAnalyzer:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.analysis = QueryAnalysis(
            booking_type="general_sale",
            ticket_delivery="onsite",
            needed_topics=["general_sale", "onsite_pickup"],
            search_query="일반예매 현장수령",
        )

    def analyze(self, question: str) -> QueryAnalysis:
        self.questions.append(question)
        return self.analysis

    def build_search_query(
        self,
        question: str,
        analysis: QueryAnalysis,
    ) -> str:
        return f"{question} {analysis.search_query}"


class FakeAnswerChain:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = TicketGuideResponse(
            summary="현장수령 준비 안내",
            schedule=[],
            requirements=["신분증"],
            ticket_info=["현장수령"],
            warnings=[],
            sources=["https://example.com/concert"],
        )

    def answer(self, **kwargs: Any) -> TicketGuideResponse:
        self.calls.append(kwargs)
        return self.response


def make_service(*, exists: bool) -> tuple[TicketGuideService, dict[str, Any]]:
    parts: dict[str, Any] = {
        "loader": FakeLoader(),
        "extractor": FakeExtractor(),
        "processor": FakeProcessor(),
        "store": FakeVectorStore(exists=exists),
        "analyzer": FakeAnalyzer(),
        "chain": FakeAnswerChain(),
    }
    service = TicketGuideService(
        loader=parts["loader"],
        image_text_extractor=parts["extractor"],
        document_processor=parts["processor"],
        vector_store=parts["store"],
        query_analyzer=parts["analyzer"],
        answer_chain=parts["chain"],
    )
    return service, parts


def test_guide_ingests_new_concert_then_runs_qa_pipeline() -> None:
    service, parts = make_service(exists=False)
    url = "https://nol.yanolja.com/ticket/products/26012624"
    question = "일반예매하고 현장에서 받을 때 뭐가 필요해?"

    result = service.guide(url=url, question=question)

    assert result == parts["chain"].response
    assert parts["loader"].loaded_urls == [url]
    assert parts["extractor"].urls == ["https://example.com/notice.jpg"]
    assert parts["processor"].built_with[1] == {
        "https://example.com/notice.jpg": "상세 이미지 OCR 안내"
    }
    assert parts["processor"].split_input == parts["processor"].documents
    assert parts["store"].index_calls == [
        ("26012624", parts["processor"].chunks)
    ]
    assert parts["store"].retrieve_calls == [
        ("26012624", f"{question} 일반예매 현장수령")
    ]
    assert parts["chain"].calls == [
        {
            "question": question,
            "analysis": parts["analyzer"].analysis,
            "documents": parts["store"].results,
        }
    ]


def test_guide_reuses_existing_index_without_ingestion() -> None:
    service, parts = make_service(exists=True)
    url = "https://nol.yanolja.com/ticket/products/26012624"

    service.guide(url=url, question="배송은 언제 시작해?")

    assert parts["loader"].loaded_urls == []
    assert parts["extractor"].urls == []
    assert parts["store"].index_calls == []
    assert len(parts["store"].retrieve_calls) == 1


def test_empty_question_is_rejected_before_ingestion() -> None:
    service, parts = make_service(exists=False)

    with pytest.raises(ValueError, match="사용자 질문을 입력해주세요"):
        service.guide(
            url="https://nol.yanolja.com/ticket/products/26012624",
            question="   ",
        )

    assert parts["loader"].loaded_urls == []
    assert parts["extractor"].urls == []
    assert parts["store"].index_calls == []


def test_missing_detail_image_uses_html_and_adds_warning() -> None:
    service, parts = make_service(exists=False)
    parts["loader"].image_urls = ()

    result = service.guide(
        url="https://nol.yanolja.com/ticket/products/26012624",
        question="공연 시간이 언제야?",
    )

    assert parts["extractor"].urls == []
    assert parts["processor"].built_with[1] == {}
    assert TicketGuideService.NO_IMAGE_WARNING in result.warnings
    assert parts["store"].index_calls


def test_ocr_failure_uses_html_and_adds_persistent_warning() -> None:
    service, parts = make_service(exists=False)
    parts["extractor"].error = OcrProcessingError("OCR failed")
    url = "https://nol.yanolja.com/ticket/products/26012624"

    first = service.guide(url=url, question="공연 시간이 언제야?")
    second = service.guide(url=url, question="배송은 언제야?")

    assert parts["processor"].built_with[1] == {}
    assert first.warnings.count(TicketGuideService.OCR_WARNING) == 1
    assert second.warnings.count(TicketGuideService.OCR_WARNING) == 1
    assert len(parts["store"].index_calls) == 1
