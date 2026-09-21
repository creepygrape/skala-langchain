from __future__ import annotations

from pydantic import BaseModel, Field


class TicketGuideRequest(BaseModel):
    """Input accepted by the concert ticket guide API."""

    url: str = Field(min_length=1)
    question: str = Field(min_length=1)
