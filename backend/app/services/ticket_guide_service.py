from __future__ import annotations

from typing import Any

from app.chains import TicketGuideChain
from app.extractors import ImageTextExtractor
from app.loaders import NolTicketLoader
from app.models import TicketGuideResponse
from app.rag import DocumentProcessor, QueryAnalyzer, VectorStoreService


class TicketGuideService:
    """Coordinate ingestion, retrieval, and grounded answer generation."""

    def __init__(
        self,
        *,
        loader: Any | None = None,
        image_text_extractor: Any | None = None,
        document_processor: Any | None = None,
        vector_store: Any | None = None,
        query_analyzer: Any | None = None,
        answer_chain: Any | None = None,
    ) -> None:
        self._loader = loader or NolTicketLoader()
        self._image_text_extractor = image_text_extractor
        self._document_processor = document_processor or DocumentProcessor()
        self._vector_store = vector_store or VectorStoreService()
        self._query_analyzer = query_analyzer or QueryAnalyzer()
        self._answer_chain = answer_chain or TicketGuideChain()

    def guide(self, *, url: str, question: str) -> TicketGuideResponse:
        """Return ticket guidance, ingesting a concert only when necessary."""
        if not question.strip():
            raise ValueError("사용자 질문을 입력해주세요.")

        concert_id = self._loader.extract_concert_id(url)

        if not self._vector_store.has_concert(concert_id):
            self._ingest(url)

        analysis = self._query_analyzer.analyze(question)
        search_query = self._query_analyzer.build_search_query(question, analysis)
        documents = self._vector_store.retrieve(concert_id, search_query)
        return self._answer_chain.answer(
            question=question,
            analysis=analysis,
            documents=documents,
        )

    def _ingest(self, url: str) -> None:
        page = self._loader.load(url)
        image_texts: dict[str, str] = {}
        if page.image_urls:
            extractor = self._get_image_text_extractor()
            image_texts = {
                image_url: extractor.extract(image_url)
                for image_url in page.image_urls
            }
        documents = self._document_processor.build_documents(page, image_texts)
        chunks = self._document_processor.split_documents(documents)
        self._vector_store.index_documents(page.concert_id, chunks)

    def _get_image_text_extractor(self) -> Any:
        if self._image_text_extractor is None:
            self._image_text_extractor = ImageTextExtractor()
        return self._image_text_extractor
