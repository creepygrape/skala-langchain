from __future__ import annotations

from collections.abc import Mapping

from langchain_core.documents import Document

from app.loaders import NolTicketPage


class DocumentProcessor:
    """Convert collected HTML and OCR text into LangChain documents."""

    @staticmethod
    def create_html_document(
        page: NolTicketPage,
        *,
        section: str = "unknown",
    ) -> Document:
        """Create a document that preserves the parsed HTML text."""
        return Document(
            page_content=page.text,
            metadata={
                "concert_id": page.concert_id,
                "source_type": "html",
                "source_url": page.source_url,
                "section": section,
            },
        )

    @staticmethod
    def create_image_document(
        *,
        concert_id: str,
        source_url: str,
        text: str,
        section: str = "unknown",
    ) -> Document:
        """Create a document that preserves text returned by OCR."""
        return Document(
            page_content=text,
            metadata={
                "concert_id": concert_id,
                "source_type": "image",
                "source_url": source_url,
                "section": section,
            },
        )

    def build_documents(
        self,
        page: NolTicketPage,
        image_texts: Mapping[str, str],
        *,
        html_section: str = "unknown",
        image_sections: Mapping[str, str] | None = None,
    ) -> list[Document]:
        """Combine HTML and successful OCR results, keeping HTML first."""
        documents = [
            self.create_html_document(page, section=html_section),
        ]
        sections = image_sections or {}

        for image_url in page.image_urls:
            if image_url not in image_texts:
                continue
            documents.append(
                self.create_image_document(
                    concert_id=page.concert_id,
                    source_url=image_url,
                    text=image_texts[image_url],
                    section=sections.get(image_url, "unknown"),
                )
            )

        return documents
