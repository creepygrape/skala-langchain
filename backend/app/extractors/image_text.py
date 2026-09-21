from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import numpy as np
import requests
from paddleocr import PaddleOCR
from PIL import Image, UnidentifiedImageError


class ImageTextExtractionError(Exception):
    """Base exception raised while extracting text from an image."""


class ImageDownloadError(ImageTextExtractionError):
    """Raised when an image cannot be downloaded or decoded."""


class OcrProcessingError(ImageTextExtractionError):
    """Raised when PaddleOCR cannot produce searchable text."""


class ImageTextExtractor:
    """Download an image and return its unmodified PaddleOCR text."""

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    }

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        ocr: Any | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._session = session or requests.Session()
        self._ocr = ocr or PaddleOCR(
            lang="korean",
            ocr_version="PP-OCRv5",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        self._timeout = timeout

    def extract(self, image_url: str) -> str:
        """Download an image, run PaddleOCR, and join recognized lines."""
        image = self._download_image(image_url)

        try:
            results = self._ocr.predict(image)
            texts = self._collect_texts(results)
        except Exception as error:
            raise OcrProcessingError("상세 공지 이미지 분석에 실패했습니다.") from error

        if not texts:
            raise OcrProcessingError(
                "상세 공지 이미지에서 텍스트를 찾지 못했습니다."
            )

        return "\n".join(texts)

    def _download_image(self, image_url: str) -> np.ndarray:
        if not isinstance(image_url, str) or not image_url.strip():
            raise ImageDownloadError("상세 공지 이미지 URL이 올바르지 않습니다.")

        parsed = urlparse(image_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ImageDownloadError("상세 공지 이미지 URL이 올바르지 않습니다.")

        try:
            response = self._session.get(
                image_url.strip(),
                headers=self._headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as source:
                image = np.asarray(source.convert("RGB"))
        except (requests.RequestException, UnidentifiedImageError, OSError) as error:
            raise ImageDownloadError(
                "상세 공지 이미지를 불러올 수 없습니다."
            ) from error

        return image

    @classmethod
    def _collect_texts(cls, results: Iterable[Any]) -> list[str]:
        texts: list[str] = []
        for result in results:
            payload = getattr(result, "json", result)
            if callable(payload):
                payload = payload()
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, Mapping):
                continue

            content = payload.get("res", payload)
            if not isinstance(content, Mapping):
                continue

            recognized = content.get("rec_texts", [])
            if not isinstance(recognized, list):
                continue

            texts.extend(
                text
                for text in recognized
                if isinstance(text, str) and text.strip()
            )
        return texts
