from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.models import TicketGuideResponse
from app.rag import QueryAnalysis


class StructuredOutputError(RuntimeError):
    """Raised when the answer cannot be parsed after one retry."""


class TicketGuideChain:
    """Generate a grounded answer from retrieved concert documents."""

    DEFAULT_MODEL = "gpt-4o-mini"
    NO_CONTEXT_MESSAGE = "예매 페이지에서 질문과 관련된 정보를 확인하지 못했습니다."
    _PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """너는 콘서트 예매 정보를 안내하는 AI 도우미다.

반드시 다음 규칙을 지켜라.
- REFERENCE DOCUMENTS만 공연 예매 정보의 근거로 사용한다.
- 문서에 없는 정보는 추측하지 말고 "예매 페이지에서 확인할 수 없습니다."라고 답한다.
- 날짜, 시간, 가격, 정책과 OCR 문자를 임의로 수정하거나 보정하지 않는다.
- HTML과 OCR 내용이 충돌하면 source_type이 html인 문서를 우선한다.
- 사용자 질문 및 조건과 직접 관련 없는 정보는 최소화한다.
- 중요한 제한사항과 준비사항은 생략하지 않는다.
- 예매 성공을 보장하지 않는다.
- sources에는 답변 작성에 실제 사용한 문서의 source_url만 넣는다.""",
            ),
            (
                "human",
                """[USER QUESTION]
{question}

[USER CONTEXT]
{user_context}

[REFERENCE DOCUMENTS]
{reference_documents}

위 자료만 근거로 사용자에게 필요한 내용을 한국어로 구조화해줘.""",
            ),
        ]
    )

    def __init__(self, *, llm: Any | None = None) -> None:
        self._llm = llm

    def answer(
        self,
        *,
        question: str,
        analysis: QueryAnalysis,
        documents: Sequence[Document],
    ) -> TicketGuideResponse:
        """Invoke the answer model with the question, conditions, and context."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("사용자 질문을 입력해주세요.")
        if not documents:
            return TicketGuideResponse(
                summary=self.NO_CONTEXT_MESSAGE,
                schedule=[],
                requirements=[],
                ticket_info=[],
                warnings=[],
                sources=[],
            )

        llm = self._llm or ChatOpenAI(model=self.DEFAULT_MODEL, temperature=0)
        chain = self._PROMPT | llm.with_structured_output(TicketGuideResponse)
        chain_input = {
            "question": normalized_question,
            "user_context": self._format_analysis(analysis),
            "reference_documents": self._format_documents(documents),
        }

        last_error: Exception | None = None
        for _ in range(2):
            try:
                result = chain.invoke(chain_input)
                if isinstance(result, TicketGuideResponse):
                    return result
                return TicketGuideResponse.model_validate(result)
            except Exception as error:
                last_error = error

        raise StructuredOutputError(
            "AI 응답을 정해진 형식으로 변환하지 못했습니다."
        ) from last_error

    @staticmethod
    def _format_analysis(analysis: QueryAnalysis) -> str:
        topics = ", ".join(analysis.needed_topics) or "unknown"
        return "\n".join(
            (
                f"booking_type: {analysis.booking_type}",
                f"ticket_delivery: {analysis.ticket_delivery}",
                f"needed_topics: {topics}",
            )
        )

    @staticmethod
    def _format_documents(documents: Sequence[Document]) -> str:
        ordered_documents = sorted(
            enumerate(documents),
            key=lambda item: (
                item[1].metadata.get("source_type") != "html",
                item[0],
            ),
        )
        formatted: list[str] = []
        for display_index, (_, document) in enumerate(ordered_documents, 1):
            metadata = document.metadata
            formatted.append(
                "\n".join(
                    (
                        f"[Document {display_index}]",
                        f"source_type: {metadata.get('source_type', 'unknown')}",
                        f"source_url: {metadata.get('source_url', 'unknown')}",
                        f"section: {metadata.get('section', 'unknown')}",
                        "content:",
                        document.page_content,
                    )
                )
            )
        return "\n\n".join(formatted)
