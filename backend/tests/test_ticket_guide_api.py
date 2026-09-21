from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.ticket_guide import get_ticket_guide_service
from app.main import app
from app.models import TicketGuideResponse


class FakeTicketGuideService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def guide(self, *, url: str, question: str) -> TicketGuideResponse:
        self.calls.append((url, question))
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
