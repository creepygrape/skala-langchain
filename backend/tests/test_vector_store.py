from __future__ import annotations

import math

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.rag import VectorStoreService


class CountingEmbeddings(Embeddings):
    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    @staticmethod
    def _vector(text: str) -> list[float]:
        return [
            float(len(text)),
            float(sum(map(ord, text)) % 997),
            float(text.count("예매")),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return self._vector(text)


class TopicEmbeddings(Embeddings):
    """Small deterministic embedding used to verify retrieval semantics."""

    TOPICS = (
        ("팬클럽", "선예매"),
        ("일반예매",),
        ("현장", "수령"),
        ("배송",),
        ("신분증", "본인확인", "준비물"),
    )

    @classmethod
    def _vector(cls, text: str) -> list[float]:
        vector = [
            float(any(keyword in text for keyword in keywords))
            for keywords in cls.TOPICS
        ]
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def make_documents(concert_id: str) -> list[Document]:
    return [
        Document(
            page_content="팬클럽 선예매 안내",
            metadata={
                "concert_id": concert_id,
                "source_type": "html",
                "source_url": f"https://example.com/{concert_id}",
                "section": "presale",
            },
        ),
        Document(
            page_content="티켓 배송 및 현장 수령 안내",
            metadata={
                "concert_id": concert_id,
                "source_type": "image",
                "source_url": f"https://example.com/{concert_id}/notice.jpg",
                "section": "ticket_delivery",
            },
        ),
    ]


def test_index_documents_embeds_and_stores_concert_chunks() -> None:
    embeddings = CountingEmbeddings()
    service = VectorStoreService(
        embeddings=embeddings,
        collection_name="test_index_documents",
    )

    indexed = service.index_documents("26012624", make_documents("26012624"))

    assert indexed is True
    assert service.has_concert("26012624") is True
    assert service.count_documents("26012624") == 2
    assert embeddings.document_calls == [
        ["팬클럽 선예매 안내", "티켓 배송 및 현장 수령 안내"]
    ]


def test_index_documents_skips_existing_concert_without_embedding_again() -> None:
    embeddings = CountingEmbeddings()
    service = VectorStoreService(
        embeddings=embeddings,
        collection_name="test_skip_existing",
    )
    documents = make_documents("26012624")

    assert service.index_documents("26012624", documents) is True
    assert service.index_documents("26012624", documents) is False

    assert service.count_documents("26012624") == 2
    assert len(embeddings.document_calls) == 1


def test_store_keeps_multiple_concerts_separated_by_metadata() -> None:
    service = VectorStoreService(
        embeddings=CountingEmbeddings(),
        collection_name="test_multiple_concerts",
    )

    service.index_documents("26012624", make_documents("26012624"))
    service.index_documents("26012479", make_documents("26012479"))

    assert service.has_concert("26012624") is True
    assert service.has_concert("26012479") is True
    assert service.has_concert("99999999") is False
    assert service.count_documents("26012624") == 2
    assert service.count_documents("26012479") == 2


def test_index_documents_enforces_requested_concert_id_metadata() -> None:
    service = VectorStoreService(
        embeddings=CountingEmbeddings(),
        collection_name="test_metadata",
    )
    documents = make_documents("wrong-id")

    service.index_documents("26012624", documents)
    stored = service.vector_store.get(where={"concert_id": "26012624"})

    assert stored["metadatas"] is not None
    assert all(
        metadata["concert_id"] == "26012624"
        for metadata in stored["metadatas"]
    )
    assert service.has_concert("wrong-id") is False


def test_index_documents_rejects_empty_document_list() -> None:
    service = VectorStoreService(
        embeddings=CountingEmbeddings(),
        collection_name="test_empty_documents",
    )

    with pytest.raises(ValueError, match="저장할 공연 문서가 없습니다"):
        service.index_documents("26012624", [])


def test_retrieve_uses_default_top_k_and_embeds_query() -> None:
    embeddings = CountingEmbeddings()
    service = VectorStoreService(
        embeddings=embeddings,
        collection_name="test_default_retriever",
    )
    documents = [
        Document(page_content=f"공연 안내 {index}", metadata={})
        for index in range(7)
    ]
    service.index_documents("26012624", documents)

    results = service.retrieve("26012624", "공연 안내")

    assert len(results) == VectorStoreService.DEFAULT_TOP_K == 5
    assert embeddings.query_calls == ["공연 안내"]


def test_retrieve_never_returns_chunks_from_another_concert() -> None:
    service = VectorStoreService(
        embeddings=TopicEmbeddings(),
        collection_name="test_retriever_concert_filter",
    )
    service.index_documents(
        "26012624",
        [Document(page_content="대상 공연 팬클럽 선예매 안내", metadata={})],
    )
    service.index_documents(
        "26012479",
        [Document(page_content="다른 공연 팬클럽 선예매 안내", metadata={})],
    )

    results = service.retrieve("26012624", "팬클럽 선예매", top_k=5)

    assert [document.page_content for document in results] == [
        "대상 공연 팬클럽 선예매 안내"
    ]
    assert all(
        document.metadata["concert_id"] == "26012624"
        for document in results
    )


def test_retrieve_selects_different_chunks_for_three_user_questions() -> None:
    service = VectorStoreService(
        embeddings=TopicEmbeddings(),
        collection_name="test_retriever_questions",
    )
    service.index_documents(
        "26012624",
        [
            Document(
                page_content="팬클럽 인증을 완료한 회원의 선예매 일정 안내",
                metadata={"section": "fanclub_presale"},
            ),
            Document(
                page_content="일반예매 후 현장 수령 시 신분증 준비물 안내",
                metadata={"section": "onsite_identity"},
            ),
            Document(
                page_content="티켓 배송 시작일과 이후 현장 수령 일정 안내",
                metadata={"section": "ticket_delivery"},
            ),
            Document(
                page_content="예매 취소 및 환불 수수료 안내",
                metadata={"section": "cancellation"},
            ),
        ],
    )
    questions = [
        "팬클럽 선예매하려면 언제 뭘 해야 해?",
        "일반예매하고 현장에서 티켓 받을 건데 준비물이 뭐야?",
        "배송은 언제 시작하고 현장수령은 언제부터 해야 해?",
    ]

    first_results = [
        service.retrieve("26012624", question, top_k=1)[0]
        for question in questions
    ]

    assert [document.metadata["section"] for document in first_results] == [
        "fanclub_presale",
        "onsite_identity",
        "ticket_delivery",
    ]


def test_get_retriever_rejects_non_positive_top_k() -> None:
    service = VectorStoreService(
        embeddings=CountingEmbeddings(),
        collection_name="test_invalid_top_k",
    )

    with pytest.raises(ValueError, match="top_k는 1 이상"):
        service.get_retriever("26012624", top_k=0)
