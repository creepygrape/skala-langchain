from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import TicketGuideRequest, TicketGuideResponse
from app.services import TicketGuideService


router = APIRouter(prefix="/api", tags=["ticket-guide"])


@lru_cache(maxsize=1)
def get_ticket_guide_service() -> TicketGuideService:
    """Reuse one in-memory Vector Store across API requests."""
    return TicketGuideService()


@router.post("/guide", response_model=TicketGuideResponse)
def create_ticket_guide(
    request: TicketGuideRequest,
    service: Annotated[TicketGuideService, Depends(get_ticket_guide_service)],
) -> TicketGuideResponse:
    """Generate a personalized guide from a NOL Ticket product page."""
    return service.guide(url=request.url, question=request.question)
