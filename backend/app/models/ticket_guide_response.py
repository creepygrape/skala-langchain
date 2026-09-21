from __future__ import annotations

from pydantic import BaseModel, Field


class TicketGuideResponse(BaseModel):
    """Structured concert ticket guidance returned to the frontend."""

    summary: str = Field(description="사용자 질문에 대한 짧은 핵심 결론")
    schedule: list[str] = Field(description="질문과 관련된 날짜와 시간")
    requirements: list[str] = Field(description="사용자가 준비하거나 수행할 사항")
    ticket_info: list[str] = Field(description="배송, 수령, 매수 제한 등 티켓 정보")
    warnings: list[str] = Field(description="놓치면 문제가 될 수 있는 제한사항")
    sources: list[str] = Field(description="답변에 실제 사용한 원문 출처 URL")
