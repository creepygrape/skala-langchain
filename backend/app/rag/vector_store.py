from __future__ import annotations

from collections.abc import Sequence

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


class VectorStoreService:
    """Embed and store concert documents in an in-memory Chroma collection."""

    DEFAULT_COLLECTION_NAME = "concert_ticket_guide"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(
        self,
        *,
        embeddings: Embeddings | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> None:
        self._embeddings = embeddings or OpenAIEmbeddings(
            model=self.DEFAULT_EMBEDDING_MODEL
        )
        self._vector_store = Chroma(
            client=chromadb.EphemeralClient(),
            collection_name=collection_name,
            embedding_function=self._embeddings,
        )

    @property
    def vector_store(self) -> Chroma:
        """Expose the configured store for the retriever phase."""
        return self._vector_store

    def has_concert(self, concert_id: str) -> bool:
        """Return whether at least one chunk exists for a concert."""
        result = self._vector_store.get(
            where={"concert_id": concert_id},
            limit=1,
            include=[],
        )
        return bool(result["ids"])

    def count_documents(self, concert_id: str) -> int:
        """Return the number of stored chunks for a concert."""
        result = self._vector_store.get(
            where={"concert_id": concert_id},
            include=[],
        )
        return len(result["ids"])

    def index_documents(
        self,
        concert_id: str,
        documents: Sequence[Document],
    ) -> bool:
        """Index a concert once and return whether new vectors were stored."""
        if self.has_concert(concert_id):
            return False
        if not documents:
            raise ValueError("저장할 공연 문서가 없습니다.")

        concert_documents = [
            Document(
                page_content=document.page_content,
                metadata={**document.metadata, "concert_id": concert_id},
            )
            for document in documents
        ]
        self._vector_store.add_documents(concert_documents)
        return True
