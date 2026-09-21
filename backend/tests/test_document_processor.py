from langchain_core.documents import Document

from app.loaders import NolTicketPage
from app.rag import DocumentProcessor


PAGE_URL = "https://nol.yanolja.com/ticket/products/26012624"
IMAGE_URL_1 = "https://ticketimage.interpark.com/Play/ITM/notice-1.jpg"
IMAGE_URL_2 = "https://ticketimage.interpark.com/Play/ITM/notice-2.jpg"
HTML_TEXT = "공연명\n공연 기간\n취소 및 환불 규정"
OCR_TEXT_1 = "N이L\n팬클럽 선예매\n12:0OPM"
OCR_TEXT_2 = "티켓 배송\n현장 수령\n본인 확인"


def make_page() -> NolTicketPage:
    return NolTicketPage(
        concert_id="26012624",
        source_url=PAGE_URL,
        text=HTML_TEXT,
        image_urls=(IMAGE_URL_1, IMAGE_URL_2),
    )


def test_create_html_document_preserves_content_and_metadata() -> None:
    document = DocumentProcessor.create_html_document(
        make_page(),
        section="basic_info",
    )

    assert isinstance(document, Document)
    assert document.page_content == HTML_TEXT
    assert document.metadata == {
        "concert_id": "26012624",
        "source_type": "html",
        "source_url": PAGE_URL,
        "section": "basic_info",
    }


def test_create_image_document_preserves_ocr_errors_and_metadata() -> None:
    document = DocumentProcessor.create_image_document(
        concert_id="26012624",
        source_url=IMAGE_URL_1,
        text=OCR_TEXT_1,
        section="presale",
    )

    assert document.page_content == OCR_TEXT_1
    assert "N이L" in document.page_content
    assert "12:0OPM" in document.page_content
    assert document.metadata == {
        "concert_id": "26012624",
        "source_type": "image",
        "source_url": IMAGE_URL_1,
        "section": "presale",
    }


def test_build_documents_combines_html_and_images_in_source_order() -> None:
    documents = DocumentProcessor().build_documents(
        make_page(),
        {
            IMAGE_URL_2: OCR_TEXT_2,
            IMAGE_URL_1: OCR_TEXT_1,
        },
        html_section="basic_info",
        image_sections={
            IMAGE_URL_1: "presale",
            IMAGE_URL_2: "ticket_delivery",
        },
    )

    assert [document.page_content for document in documents] == [
        HTML_TEXT,
        OCR_TEXT_1,
        OCR_TEXT_2,
    ]
    assert [document.metadata["source_type"] for document in documents] == [
        "html",
        "image",
        "image",
    ]
    assert [document.metadata["section"] for document in documents] == [
        "basic_info",
        "presale",
        "ticket_delivery",
    ]


def test_build_documents_keeps_html_when_image_ocr_is_missing() -> None:
    documents = DocumentProcessor().build_documents(make_page(), {})

    assert len(documents) == 1
    assert documents[0].page_content == HTML_TEXT
    assert documents[0].metadata["source_type"] == "html"
    assert documents[0].metadata["section"] == "unknown"
