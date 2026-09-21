from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.chains import TicketGuideChain
from app.rag import QueryAnalysis


class RecordingLlm:
    def __init__(self, answer: str = "근거 기반 답변") -> None:
        self.answer = answer
        self.prompts: list[Any] = []
        self.runnable = RunnableLambda(self._invoke)

    def _invoke(self, prompt: Any) -> AIMessage:
        self.prompts.append(prompt)
        return AIMessage(content=self.answer)


def make_analysis() -> QueryAnalysis:
    return QueryAnalysis(
        booking_type="general_sale",
        ticket_delivery="onsite",
        needed_topics=[
            "general_sale",
            "onsite_pickup",
            "identity_verification",
        ],
        search_query="일반예매 현장수령 본인확인",
    )


def make_documents() -> list[Document]:
    return [
        Document(
            page_content="현징 수령은 18:0OPM부터 가능합니다.",
            metadata={
                "source_type": "image",
                "source_url": "https://example.com/notice.jpg",
                "section": "onsite_pickup",
            },
        ),
        Document(
            page_content="현장 수령 시 실물 신분증과 예매내역서가 필요합니다.",
            metadata={
                "source_type": "html",
                "source_url": "https://example.com/concert",
                "section": "onsite_pickup",
            },
        ),
    ]


def prompt_text(llm: RecordingLlm) -> str:
    return "\n".join(
        str(message.content)
        for message in llm.prompts[0].to_messages()
    )


def test_answer_passes_question_analysis_and_documents_to_llm() -> None:
    recording = RecordingLlm("실물 신분증과 예매내역서를 준비하세요.")
    chain = TicketGuideChain(llm=recording.runnable)

    result = chain.answer(
        question="일반예매 후 현장에서 받을 때 뭘 준비해야 해?",
        analysis=make_analysis(),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert result == "실물 신분증과 예매내역서를 준비하세요."
    assert "일반예매 후 현장에서 받을 때 뭘 준비해야 해?" in rendered
    assert "booking_type: general_sale" in rendered
    assert "ticket_delivery: onsite" in rendered
    assert "general_sale, onsite_pickup, identity_verification" in rendered
    assert "실물 신분증과 예매내역서" in rendered


def test_answer_preserves_ocr_text_and_source_metadata() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording.runnable)

    chain.answer(
        question="현장수령 시간은 언제야?",
        analysis=QueryAnalysis(search_query="현장수령 시간"),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert "현징 수령은 18:0OPM부터 가능합니다." in rendered
    assert "source_type: image" in rendered
    assert "source_url: https://example.com/notice.jpg" in rendered
    assert "section: onsite_pickup" in rendered


def test_html_context_is_placed_before_image_context() -> None:
    formatted = TicketGuideChain._format_documents(make_documents())

    assert formatted.index("source_type: html") < formatted.index(
        "source_type: image"
    )


def test_prompt_contains_grounding_and_ocr_rules() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording.runnable)

    chain.answer(
        question="배송은 언제야?",
        analysis=QueryAnalysis(search_query="배송"),
        documents=make_documents(),
    )

    rendered = prompt_text(recording)
    assert "REFERENCE DOCUMENTS만" in rendered
    assert "문서에 없는 정보는 추측하지 말고" in rendered
    assert "날짜, 시간, 가격, 정책과 OCR 문자를 임의로 수정" in rendered
    assert "source_type이 html인 문서를 우선" in rendered
    assert "사용자 질문 및 조건과 직접 관련 없는 정보는 최소화" in rendered


def test_empty_documents_return_message_without_llm_call() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording.runnable)

    result = chain.answer(
        question="없는 정보를 알려줘",
        analysis=QueryAnalysis(search_query="없는 정보"),
        documents=[],
    )

    assert result == TicketGuideChain.NO_CONTEXT_MESSAGE
    assert recording.prompts == []


def test_empty_question_is_rejected_without_llm_call() -> None:
    recording = RecordingLlm()
    chain = TicketGuideChain(llm=recording.runnable)

    try:
        chain.answer(
            question="   ",
            analysis=QueryAnalysis(search_query="질문"),
            documents=make_documents(),
        )
    except ValueError as error:
        assert str(error) == "사용자 질문을 입력해주세요."
    else:
        raise AssertionError("빈 질문은 거부되어야 합니다.")

    assert recording.prompts == []
