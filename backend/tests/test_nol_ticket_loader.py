from unittest.mock import Mock

import pytest
import requests

from app.loaders.nol_ticket import (
    InvalidNolTicketUrlError,
    NolTicketLoader,
    PageFetchError,
    PageParseError,
)


PRODUCT_URL = "https://nol.yanolja.com/ticket/products/26012624"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (PRODUCT_URL, "26012624"),
        (f"{PRODUCT_URL}/", "26012624"),
        (f"{PRODUCT_URL}?language=ko", "26012624"),
    ],
)
def test_extract_concert_id(url: str, expected: str) -> None:
    assert NolTicketLoader.extract_concert_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "http://nol.yanolja.com/ticket/products/26012624",
        "https://example.com/ticket/products/26012624",
        "https://nol.yanolja.com/ticket/products/not-a-number",
        "https://nol.yanolja.com/ticket/products/26012624/extra",
        "https://nol.yanolja.com:443/ticket/products/26012624",
        "https://user@nol.yanolja.com/ticket/products/26012624",
    ],
)
def test_extract_concert_id_rejects_unsupported_url(url: str) -> None:
    with pytest.raises(InvalidNolTicketUrlError):
        NolTicketLoader.extract_concert_id(url)


def test_load_extracts_text_and_detail_images() -> None:
    html = """
    <html>
      <head>
        <style>.hidden { display: none; }</style>
        <script>const secret = 'not page text';</script>
      </head>
      <body>
        <h1>DAY6 FANMEETING</h1>
        <p>팬클럽 선예매는 오후 8시입니다.</p>
        <img src="https://ticketimage.interpark.com/Play/image/large/26/poster.gif">
        <img src="https://ticketimage.interpark.com/Play/ITM/Data/notice-1.jpg">
        <img data-src="//ticketimage.interpark.com/Play/ITM/Data/notice-2.jpg">
        <img src="https://ticketimage.interpark.com/Play/ITM/Data/notice-1.jpg">
        <img src="https://example.com/unrelated.jpg">
      </body>
    </html>
    """
    session = Mock(spec=requests.Session)
    response = Mock()
    response.url = PRODUCT_URL
    response.text = html
    response.raise_for_status.return_value = None
    session.get.return_value = response

    page = NolTicketLoader(session=session, timeout=5).load(PRODUCT_URL)

    assert page.concert_id == "26012624"
    assert page.source_url == PRODUCT_URL
    assert "DAY6 FANMEETING" in page.text
    assert "팬클럽 선예매는 오후 8시입니다." in page.text
    assert "not page text" not in page.text
    assert page.image_urls == (
        "https://ticketimage.interpark.com/Play/ITM/Data/notice-1.jpg",
        "https://ticketimage.interpark.com/Play/ITM/Data/notice-2.jpg",
    )
    session.get.assert_called_once_with(
        PRODUCT_URL,
        headers=NolTicketLoader._headers,
        timeout=5,
    )


def test_load_wraps_request_failure() -> None:
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("timed out")

    with pytest.raises(PageFetchError):
        NolTicketLoader(session=session).load(PRODUCT_URL)


def test_load_rejects_redirect_outside_product_page() -> None:
    session = Mock(spec=requests.Session)
    response = Mock()
    response.url = "https://nol.yanolja.com/error"
    response.text = "error"
    response.raise_for_status.return_value = None
    session.get.return_value = response

    with pytest.raises(PageFetchError):
        NolTicketLoader(session=session).load(PRODUCT_URL)


def test_parse_rejects_page_without_text() -> None:
    with pytest.raises(PageParseError):
        NolTicketLoader.parse(
            html="<html><script>only script content</script></html>",
            source_url=PRODUCT_URL,
            concert_id="26012624",
        )
