from __future__ import annotations

from typing import Any

import pytest
from langchain_core.runnables import RunnableLambda

from app.rag import QueryAnalysis, QueryAnalysisError, QueryAnalyzer


class FakeStructuredLlm:
    def __init__(self, response: QueryAnalysis) -> None:
        self.response = response
        self.schema: type[QueryAnalysis] | None = None
        self.calls: list[Any] = []

    def with_structured_output(
        self,
        schema: type[QueryAnalysis],
    ) -> RunnableLambda:
        self.schema = schema

        def respond(prompt: Any) -> QueryAnalysis:
            self.calls.append(prompt)
            return self.response

        return RunnableLambda(respond)


def test_simple_question_uses_original_query_without_llm() -> None:
    llm = FakeStructuredLlm(
        QueryAnalysis(
            needed_topics=["ticket_delivery"],
            search_query="티켓 배송",
        )
    )
    analyzer = QueryAnalyzer(llm=llm)

    result = analyzer.analyze("티켓 배송은 언제 시작해?")

    assert result == QueryAnalysis(search_query="티켓 배송은 언제 시작해?")
    assert llm.calls == []


def test_compound_question_returns_structured_conditions() -> None:
    expected = QueryAnalysis(
        booking_type="fanclub_presale",
        ticket_delivery="onsite",
        needed_topics=[
            "fanclub_verification",
            "presale",
            "onsite_pickup",
            "identity_verification",
        ],
        search_query="팬클럽 인증 선예매 현장수령 본인확인",
    )
    llm = FakeStructuredLlm(expected)
    analyzer = QueryAnalyzer(llm=llm)

    result = analyzer.analyze(
        "팬클럽 선예매 할 거고 현장수령 예정인데 언제 뭘 해야 해?"
    )

    assert result == expected
    assert llm.schema is QueryAnalysis
    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    "question",
    [
        "일반예매하고 현장에서 표 받을 때 신분증을 챙겨야 해?",
        "배송은 언제 시작하고 취소 수수료는 얼마야?",
    ],
)
def test_multiple_information_topics_are_compound(question: str) -> None:
    assert QueryAnalyzer.is_compound(question) is True


def test_build_search_query_preserves_original_question() -> None:
    analysis = QueryAnalysis(
        booking_type="general_sale",
        ticket_delivery="onsite",
        needed_topics=["general_sale", "onsite_pickup"],
        search_query="일반예매 현장수령",
    )

    search_query = QueryAnalyzer.build_search_query(
        "일반예매 후 현장에서 받을 거야",
        analysis,
    )

    assert search_query == (
        "일반예매 후 현장에서 받을 거야 일반예매 현장수령"
    )


def test_build_search_query_does_not_duplicate_unchanged_query() -> None:
    question = "취소 수수료 알려줘"
    analysis = QueryAnalysis(search_query=question)

    assert QueryAnalyzer.build_search_query(question, analysis) == question


def test_empty_question_is_rejected() -> None:
    analyzer = QueryAnalyzer(llm=FakeStructuredLlm(QueryAnalysis(search_query="x")))

    with pytest.raises(ValueError, match="사용자 질문을 입력해주세요"):
        analyzer.analyze("  ")


def test_compound_question_wraps_llm_failure() -> None:
    class FailingLlm:
        def with_structured_output(self, schema: Any) -> RunnableLambda:
            def fail(prompt: Any) -> QueryAnalysis:
                raise RuntimeError("LLM unavailable")

            return RunnableLambda(fail)

    analyzer = QueryAnalyzer(llm=FailingLlm())

    with pytest.raises(QueryAnalysisError, match="사용자 질문을 분석하지 못했습니다"):
        analyzer.analyze("배송받고 취소도 하고 싶어")
