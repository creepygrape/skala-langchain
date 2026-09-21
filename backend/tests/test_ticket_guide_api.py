from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.chains import StructuredOutputError
from app.api.ticket_guide import get_ticket_guide_service
from app.loaders import InvalidNolTicketUrlError, PageFetchError
from app.main import app
from app.models import TicketGuideResponse


class FakeTicketGuideService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.error: Exception | None = None

    def guide(self, *, url: str, question: str) -> TicketGuideResponse:
        self.calls.append((url, question))
        if self.error is not None:
            raise self.error
        return TicketGuideResponse(
            summary="팬클럽 선예매 안내",
            schedule=["선예매 일정"],
            requirements=["팬클럽 인증"],
            ticket_info=[],
            warnings=["인증 기간 이후 인증 불가"],
            sources=[url],
        )


def test_post_guide_returns_structured_response() -> None:
    service = FakeTicketGuideService()
    app.dependency_overrides[get_ticket_guide_service] = lambda: service
    client = TestClient(app)
    payload = {
        "url": "https://nol.yanolja.com/ticket/products/26012624",
        "question": "팬클럽 선예매는 언제야?",
    }

    try:
        response = client.post("/api/guide", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "summary": "팬클럽 선예매 안내",
        "schedule": ["선예매 일정"],
        "requirements": ["팬클럽 인증"],
        "ticket_info": [],
        "warnings": ["인증 기간 이후 인증 불가"],
        "sources": [payload["url"]],
    }
    assert service.calls == [(payload["url"], payload["question"])]


def test_post_guide_rejects_missing_question() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/guide",
        json={"url": "https://nol.yanolja.com/ticket/products/26012624"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            InvalidNolTicketUrlError("현재는 NOL Ticket 상품 페이지만 지원합니다."),
            400,
            "현재는 NOL Ticket 상품 페이지만 지원합니다.",
        ),
        (
            PageFetchError(
                "예매 페이지를 불러올 수 없습니다. URL을 확인해주세요."
            ),
            502,
            "예매 페이지를 불러올 수 없습니다. URL을 확인해주세요.",
        ),
        (
            StructuredOutputError("invalid output"),
            502,
            "AI 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ),
    ],
)
def test_post_guide_maps_domain_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    service = FakeTicketGuideService()
    service.error = error
    app.dependency_overrides[get_ticket_guide_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/guide",
            json={
                "url": "https://example.com/not-supported",
                "question": "선예매는 언제야?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
