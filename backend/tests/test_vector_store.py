from __future__ import annotations

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
