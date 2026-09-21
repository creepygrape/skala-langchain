from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.chains import StructuredOutputError
from app.loaders import InvalidNolTicketUrlError, PageFetchError, PageParseError
from app.models import TicketGuideRequest, TicketGuideResponse
from app.rag import QueryAnalysisError
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
    try:
        return service.guide(url=request.url, question=request.question)
    except (InvalidNolTicketUrlError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except (PageFetchError, PageParseError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except (QueryAnalysisError, StructuredOutputError, OpenAIError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ) from error
