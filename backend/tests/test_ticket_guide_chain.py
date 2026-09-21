from __future__ import annotations

from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.chains import StructuredOutputError, TicketGuideChain
from app.models import TicketGuideResponse
from app.rag import QueryAnalysis


class RecordingLlm:
    def __init__(self, *results: TicketGuideResponse | Exception) -> None:
        self.results = list(results) or [make_response()]
        self.prompts: list[Any] = []
        self.schema: type[TicketGuideResponse] | None = None

    def with_structured_output(
        self,
        schema: type[TicketGuideResponse],
    ) -> RunnableLambda:
        self.schema = schema
        return RunnableLambda(self._invoke)

    def _invoke(self, prompt: Any) -> TicketGuideResponse:
        self.prompts.append(prompt)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def make_response() -> TicketGuideResponse:
    return TicketGuideResponse(
        summary="실물 신분증과 예매내역서를 준비하세요.",
        schedule=[],
        requirements=["실물 신분증", "예매내역서"],
        ticket_info=["현장 수령"],
        warnings=[],
        sources=["https://example.com/concert"],
    )


def make_analysis() -> QueryAnalysis:
    return QueryAnalysis(
        booking_type="general_sale",
        ticket_delivery="onsite",
        needed_topics=[
            "general_sale",
            "onsite_pickup",
            "identity_verification",
        ],
        search_query="일반예매 현장수령 본인확인",
    )


def make_documents() -> list[Document]:
    return [
        Document(
            page_content="현징 수령은 18:0OPM부터 가능합니다.",
            metadata={
                "source_type": "image",
                "source_url": "https://example.com/notice.jpg",
                "section": "onsite_pickup",
            },
        ),
        Document(
            page_content="현장 수령 시 실물 신분증과 예매내역서가 필요합니다.",
            metadata={
                "source_type": "html",
                "source_url": "https://example.com/concert",
                "section": "onsite_pickup",
            },
        ),
    ]


def prompt_text(llm: RecordingLlm) -> str:
    return "\n".join(
        str(message.content)
        for message in llm.prompts[0].to_messages()
    )


def test_answer_passes_question_analysis_and_documents_to_llm() -> None:
    expected = make_response()
    recording = RecordingLlm(expected)
    chain = TicketGuideChain(llm=recording)

    result = chain.answer(
        question="일반예매 후 현장에서 받을 때 뭘 준비해야 해?",
        analysis=make_analysis(),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert result == expected
    assert recording.schema is TicketGuideResponse
    assert "일반예매 후 현장에서 받을 때 뭘 준비해야 해?" in rendered
    assert "booking_type: general_sale" in rendered
    assert "ticket_delivery: onsite" in rendered
    assert "general_sale, onsite_pickup, identity_verification" in rendered
    assert "실물 신분증과 예매내역서" in rendered


def test_answer_preserves_ocr_text_and_source_metadata() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording)

    chain.answer(
        question="현장수령 시간은 언제야?",
        analysis=QueryAnalysis(search_query="현장수령 시간"),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert "현징 수령은 18:0OPM부터 가능합니다." in rendered
    assert "source_type: image" in rendered
    assert "source_url: https://example.com/notice.jpg" in rendered
    assert "section: onsite_pickup" in rendered


def test_html_context_is_placed_before_image_context() -> None:
    formatted = TicketGuideChain._format_documents(make_documents())

    assert formatted.index("source_type: html") < formatted.index(
        "source_type: image"
    )


def test_prompt_contains_grounding_and_ocr_rules() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording)

    chain.answer(
        question="배송은 언제야?",
        analysis=QueryAnalysis(search_query="배송"),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert "REFERENCE DOCUMENTS만" in rendered
    assert "날짜, 시간, 가격, 정책과 OCR 문자를 임의로 수정" in rendered
    assert "HTML 값만 사용하고 OCR 값은 답변에서 제외" in rendered
    assert "SUPPLEMENTAL OCR DOCUMENTS는 HTML 문서에 없는 정보" in rendered
    assert "직접 답하는 정보만" in rendered
    assert "summary를 정확히 \"예매 페이지에서 확인할 수 없습니다.\"" in rendered


def test_empty_documents_return_message_without_llm_call() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording)

    result = chain.answer(
        question="없는 정보를 알려줘",
        analysis=QueryAnalysis(search_query="없는 정보"),
        documents=[],
    )

    assert result == TicketGuideResponse(
        summary=TicketGuideChain.NO_CONTEXT_MESSAGE,
        schedule=[],
        requirements=[],
        ticket_info=[],
        warnings=[],
        sources=[],
    )
    assert recording.prompts == []


def test_empty_question_is_rejected_without_llm_call() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording)

    with pytest.raises(ValueError, match="사용자 질문을 입력해주세요"):
        chain.answer(
            question="   ",
            analysis=QueryAnalysis(search_query="질문"),
            documents=make_documents(),
        )

    assert recording.prompts == []


def test_structured_output_failure_is_retried_once() -> None:
    expected = make_response()
    recording = RecordingLlm(ValueError("invalid output"), expected)
    chain = TicketGuideChain(llm=recording)

    result = chain.answer(
        question="현장수령 준비물이 뭐야?",
        analysis=make_analysis(),
        documents=make_documents(),
    )

    assert result == expected
    assert len(recording.prompts) == 2


def test_structured_output_fails_after_one_retry() -> None:
    recording = RecordingLlm(
        ValueError("first invalid output"),
        ValueError("second invalid output"),
    )
    chain = TicketGuideChain(llm=recording)

    with pytest.raises(
        StructuredOutputError,
        match="AI 응답을 정해진 형식으로 변환하지 못했습니다",
    ):
        chain.answer(
            question="현장수령 준비물이 뭐야?",
            analysis=make_analysis(),
            documents=make_documents(),
        )

    assert len(recording.prompts) == 2


def test_not_found_response_discards_unrelated_generated_details() -> None:
    generated = TicketGuideResponse(
        summary=TicketGuideChain.NOT_FOUND_MESSAGE,
        schedule=["관련 없는 공연 일정"],
        requirements=["관련 없는 준비사항"],
        ticket_info=["관련 없는 가격"],
        warnings=["관련 없는 주의사항"],
        sources=["https://example.com/concert"],
    )
    recording = RecordingLlm(generated)
    chain = TicketGuideChain(llm=recording)

    result = chain.answer(
        question="팬클럽 회원이면 굿즈를 무료로 줘?",
        analysis=QueryAnalysis(search_query="팬클럽 굿즈 무료"),
        documents=make_documents(),
    )

    assert result == TicketGuideResponse(
        summary=TicketGuideChain.NOT_FOUND_MESSAGE,
        schedule=[],
        requirements=[],
        ticket_info=[],
        warnings=[],
        sources=[],
    )
