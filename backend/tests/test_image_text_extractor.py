from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
import pytest
import requests
from PIL import Image

from app.extractors.image_text import (
    ImageDownloadError,
    ImageTextExtractor,
    OcrProcessingError,
)


IMAGE_URL = "https://ticketimage.interpark.com/Play/ITM/Data/notice.jpg"


def make_image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 3), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def make_session(content: bytes | None = None) -> Mock:
    session = Mock(spec=requests.Session)
    response = Mock()
    response.content = content if content is not None else make_image_bytes()
    response.raise_for_status.return_value = None
    session.get.return_value = response
    return session


def test_default_ocr_uses_required_korean_v5_configuration() -> None:
    with patch("app.extractors.image_text.PaddleOCR") as paddle_ocr:
        ImageTextExtractor(session=make_session())

    paddle_ocr.assert_called_once_with(
        lang="korean",
        ocr_version="PP-OCRv5",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def test_default_ocr_wraps_initialization_failure() -> None:
    with patch(
        "app.extractors.image_text.PaddleOCR",
        side_effect=RuntimeError("model unavailable"),
    ):
        with pytest.raises(OcrProcessingError):
            ImageTextExtractor(session=make_session())


def test_extract_downloads_image_and_returns_recognized_lines() -> None:
    session = make_session()
    result = Mock()
    result.json = {
        "res": {
            "rec_texts": [
                "팬클럽 인증",
                "",
                "선예매 8PM",
                "현장수령 시 신분증 지참",
            ]
        }
    }
    ocr = Mock()
    ocr.predict.return_value = [result]

    text = ImageTextExtractor(
        session=session,
        ocr=ocr,
        timeout=5,
    ).extract(IMAGE_URL)

    assert text == "팬클럽 인증\n선예매 8PM\n현장수령 시 신분증 지참"
    session.get.assert_called_once_with(
        IMAGE_URL,
        headers=ImageTextExtractor._headers,
        timeout=5,
    )
    image = ocr.predict.call_args.args[0]
    assert isinstance(image, np.ndarray)
    assert image.shape == (3, 4, 3)


@pytest.mark.parametrize("image_url", ["", "not-a-url", "file:///tmp/a.jpg"])
def test_extract_rejects_invalid_image_url(image_url: str) -> None:
    with pytest.raises(ImageDownloadError):
        ImageTextExtractor(session=make_session(), ocr=Mock()).extract(image_url)


def test_extract_wraps_download_failure() -> None:
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("timed out")

    with pytest.raises(ImageDownloadError):
        ImageTextExtractor(session=session, ocr=Mock()).extract(IMAGE_URL)


def test_extract_rejects_non_image_response() -> None:
    with pytest.raises(ImageDownloadError):
        ImageTextExtractor(
            session=make_session(b"not an image"),
            ocr=Mock(),
        ).extract(IMAGE_URL)


def test_extract_wraps_ocr_failure() -> None:
    ocr = Mock()
    ocr.predict.side_effect = RuntimeError("OCR failed")

    with pytest.raises(OcrProcessingError):
        ImageTextExtractor(session=make_session(), ocr=ocr).extract(IMAGE_URL)


def test_extract_rejects_empty_ocr_result() -> None:
    result = Mock()
    result.json = {"res": {"rec_texts": []}}
    ocr = Mock()
    ocr.predict.return_value = [result]

    with pytest.raises(OcrProcessingError):
        ImageTextExtractor(session=make_session(), ocr=ocr).extract(IMAGE_URL)
