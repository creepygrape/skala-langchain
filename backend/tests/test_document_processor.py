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


def test_split_documents_uses_configured_size_and_preserves_metadata() -> None:
    document = Document(
        page_content="\n".join(f"공연 안내 문장 {index}" for index in range(120)),
        metadata={
            "concert_id": "26012624",
            "source_type": "html",
            "source_url": PAGE_URL,
            "section": "notice",
        },
    )

    chunks = DocumentProcessor(chunk_size=200, chunk_overlap=30).split_documents(
        [document]
    )

    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 200 for chunk in chunks)
    assert all(chunk.metadata == document.metadata for chunk in chunks)


def test_split_documents_keeps_related_notice_lines_together() -> None:
    fanclub_notice = """[팬클럽 인증 안내]
- 인증 기간: 9월 8일부터 9월 17일까지
- 인증 대상: My Day 6기 회원
- 인증 방법: 본인 명의 계정으로 인증
※ 인증 기간 이후에는 인증할 수 없습니다."""
    other_notice = "\n\n[기타 안내]\n" + "별도 안내입니다. " * 100
    document = Document(
        page_content=fanclub_notice + other_notice,
        metadata={
            "concert_id": "26012624",
            "source_type": "image",
            "source_url": IMAGE_URL_1,
            "section": "fanclub_verification",
        },
    )

    chunks = DocumentProcessor().split_documents([document])

    assert any(fanclub_notice in chunk.page_content for chunk in chunks)


def test_split_documents_keeps_html_before_image_chunks() -> None:
    page = NolTicketPage(
        concert_id="26012624",
        source_url=PAGE_URL,
        text="HTML 공연 정보 " * 120,
        image_urls=(IMAGE_URL_1,),
    )
    processor = DocumentProcessor(chunk_size=200, chunk_overlap=30)
    documents = processor.build_documents(page, {IMAGE_URL_1: "OCR 상세 공지 " * 120})

    chunks = processor.split_documents(documents)
    source_types = [chunk.metadata["source_type"] for chunk in chunks]

    first_image_index = source_types.index("image")
    assert all(source_type == "html" for source_type in source_types[:first_image_index])
    assert all(source_type == "image" for source_type in source_types[first_image_index:])
