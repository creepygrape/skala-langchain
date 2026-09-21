from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


_PRODUCT_PATH = re.compile(r"^/ticket/products/(?P<concert_id>[0-9]+)/?$")
_DETAIL_IMAGE_HOST = "ticketimage.interpark.com"
_DETAIL_IMAGE_PATH_PREFIX = "/play/itm/"


class NolTicketLoaderError(Exception):
    """Base exception raised while loading a NOL Ticket product page."""


class InvalidNolTicketUrlError(NolTicketLoaderError):
    """Raised when a URL is not a supported NOL Ticket product URL."""


class PageFetchError(NolTicketLoaderError):
    """Raised when a product page cannot be fetched."""


class PageParseError(NolTicketLoaderError):
    """Raised when product information cannot be parsed from the page."""


@dataclass(frozen=True)
class NolTicketPage:
    concert_id: str
    source_url: str
    text: str
    image_urls: tuple[str, ...]


class NolTicketLoader:
    """Load text and detail image URLs from a NOL Ticket product page."""

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout

    @staticmethod
    def extract_concert_id(url: str) -> str:
        """Validate a supported product URL and return its concert ID."""
        if not isinstance(url, str) or not url.strip():
            raise InvalidNolTicketUrlError("NOL Ticket 상품 URL을 입력해주세요.")

        try:
            parsed = urlparse(url.strip())
            port = parsed.port
        except ValueError as error:
            raise InvalidNolTicketUrlError("URL 형식이 올바르지 않습니다.") from error

        if (
            parsed.scheme != "https"
            or parsed.hostname != "nol.yanolja.com"
            or port is not None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise InvalidNolTicketUrlError(
                "현재는 NOL Ticket 상품 페이지만 지원합니다."
            )

        match = _PRODUCT_PATH.fullmatch(parsed.path)
        if match is None:
            raise InvalidNolTicketUrlError(
                "현재는 NOL Ticket 상품 페이지만 지원합니다."
            )

        return match.group("concert_id")

    def load(self, url: str) -> NolTicketPage:
        """Fetch and parse a NOL Ticket product page."""
        normalized_url = url.strip() if isinstance(url, str) else url
        concert_id = self.extract_concert_id(normalized_url)

        try:
            response = self._session.get(
                normalized_url,
                headers=self._headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise PageFetchError(
                "예매 페이지를 불러올 수 없습니다. URL을 확인해주세요."
            ) from error

        try:
            self.extract_concert_id(response.url)
        except InvalidNolTicketUrlError as error:
            raise PageFetchError(
                "예매 페이지를 불러올 수 없습니다. URL을 확인해주세요."
            ) from error

        return self.parse(
            html=response.text,
            source_url=normalized_url,
            concert_id=concert_id,
        )

    @staticmethod
    def parse(*, html: str, source_url: str, concert_id: str) -> NolTicketPage:
        """Parse product text and detail image URLs from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        for element in soup(["script", "style", "noscript", "template"]):
            element.decompose()

        text = soup.get_text("\n", strip=True)
        if not text:
            raise PageParseError("페이지에서 공연 정보를 가져올 수 없습니다.")

        image_urls: list[str] = []
        for image in soup.find_all("img"):
            candidate = image.get("src") or image.get("data-src")
            if not isinstance(candidate, str):
                continue

            absolute_url = urljoin(source_url, candidate.strip())
            parsed_image_url = urlparse(absolute_url)
            if (
                parsed_image_url.scheme in {"http", "https"}
                and parsed_image_url.hostname == _DETAIL_IMAGE_HOST
                and parsed_image_url.path.lower().startswith(
                    _DETAIL_IMAGE_PATH_PREFIX
                )
                and absolute_url not in image_urls
            ):
                image_urls.append(absolute_url)

        return NolTicketPage(
            concert_id=concert_id,
            source_url=source_url,
            text=text,
            image_urls=tuple(image_urls),
        )
