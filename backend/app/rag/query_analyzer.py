from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


BookingType = Literal["fanclub_presale", "general_sale", "unknown"]
TicketDelivery = Literal["delivery", "onsite", "unknown"]
QueryTopic = Literal[
    "fanclub_verification",
    "presale",
    "general_sale",
    "ticket_delivery",
    "onsite_pickup",
    "identity_verification",
    "cancellation",
    "admission",
    "performance_schedule",
]


class QueryAnalysisError(RuntimeError):
    """Raised when a compound question cannot be analyzed."""


class QueryAnalysis(BaseModel):
    """Structured user conditions used to improve document retrieval."""

    booking_type: BookingType = "unknown"
    ticket_delivery: TicketDelivery = "unknown"
    needed_topics: list[QueryTopic] = Field(default_factory=list)
    search_query: str


class QueryAnalyzer:
    """Analyze compound questions while bypassing the LLM for simple ones."""

    DEFAULT_MODEL = "gpt-4o-mini"
    _TOPIC_SIGNALS: tuple[tuple[str, ...], ...] = (
        ("팬클럽", "선예매", "사전인증", "사전 인증"),
        ("일반예매", "일반 예매"),
        ("배송", "택배"),
        ("현장수령", "현장 수령", "현장에서", "표 받을"),
        ("본인확인", "본인 확인", "신분증", "준비물", "챙겨"),
        ("취소", "환불", "수수료"),
        ("입장", "관람"),
        ("공연일", "공연 일", "공연시간", "공연 시간", "회차"),
    )
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """너는 콘서트 예매 질문을 검색 조건으로 변환한다.
질문에 명시된 조건만 분류하고 공연의 날짜, 시간, 가격 또는 정책을 만들지 않는다.
needed_topics에는 질문에 답하는 데 필요한 주제만 넣는다.
일반예매는 general_sale, 배송은 ticket_delivery, 현장수령은 onsite_pickup으로 분류한다.
현장수령 준비물·신분증·본인확인을 물으면 identity_verification을 반드시 포함한다.
search_query에는 원문 질문의 의미를 유지하면서 검색에 유용한 한국어 핵심어를 넣는다.""",
            ),
            ("human", "사용자 질문:\n{question}"),
        ]
    )

    def __init__(self, *, llm: Any | None = None) -> None:
        self._llm = llm

    @classmethod
    def is_compound(cls, question: str) -> bool:
        """Return whether a question spans at least two information topics."""
        normalized = question.strip()
        matched_topics = sum(
            any(signal in normalized for signal in signals)
            for signals in cls._TOPIC_SIGNALS
        )
        return matched_topics >= 2

    def analyze(self, question: str) -> QueryAnalysis:
        """Return original-query retrieval for simple questions, else use LLM."""
        normalized = question.strip()
        if not normalized:
            raise ValueError("사용자 질문을 입력해주세요.")

        if not self.is_compound(normalized):
            return QueryAnalysis(search_query=normalized)

        llm = self._llm or ChatOpenAI(model=self.DEFAULT_MODEL, temperature=0)
        chain = self._PROMPT | llm.with_structured_output(QueryAnalysis)
        try:
            result = chain.invoke({"question": normalized})
            if isinstance(result, QueryAnalysis):
                return result
            return QueryAnalysis.model_validate(result)
        except Exception as error:
            raise QueryAnalysisError("사용자 질문을 분석하지 못했습니다.") from error

    @staticmethod
    def build_search_query(
        original_question: str,
        analysis: QueryAnalysis,
    ) -> str:
        """Keep the original wording and append structured retrieval keywords."""
        parts: Sequence[str] = (
            original_question.strip(),
            analysis.search_query.strip(),
        )
        return " ".join(dict.fromkeys(part for part in parts if part))
