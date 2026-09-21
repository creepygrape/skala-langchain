from __future__ import annotations

from pydantic import BaseModel, Field


class TicketGuideResponse(BaseModel):
    """Structured concert ticket guidance returned to the frontend."""

    summary: str = Field(description="사용자 질문에 대한 짧은 핵심 결론")
    schedule: list[str] = Field(description="질문에 직접 답하는 날짜와 시간만 포함")
    requirements: list[str] = Field(description="질문과 직접 관련해 준비하거나 수행할 사항")
    ticket_info: list[str] = Field(description="질문과 직접 관련된 배송, 수령, 매수 제한 정보")
    warnings: list[str] = Field(description="질문과 직접 관련해 놓치면 문제가 되는 제한사항")
    sources: list[str] = Field(description="답변에 실제 사용한 원문 출처 URL")
