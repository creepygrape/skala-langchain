# 맞춤형 콘서트 예매 가이드 — Implementation Tasks

## 구현 원칙

구현 전 다음 문서를 반드시 확인한다.

~~~text
docs/requirements.md
docs/architecture.md
docs/technical-validation.md
~~~

문서에 없는 기능을 임의로 추가하지 않는다.
각 Phase 완료 후 기능을 검증한 뒤 다음 Phase로 진행한다.

---

## Phase 1. 프로젝트 기본 구성

- Backend: FastAPI 프로젝트 구성 및 GET /health 구현
- Frontend: Vue + Vite 프로젝트 구성
- Vue → FastAPI 통신 확인

완료 조건: Vue 실행, FastAPI 실행, Frontend/Backend 통신 성공.

---

## Phase 2. NOL Ticket Loader

NolTicketLoader를 구현한다.

기능:
- NOL Ticket URL Validation
- concert_id 추출
- requests를 이용한 HTML 요청
- BeautifulSoup HTML Parsing
- 페이지 텍스트 추출
- 상세 공지 이미지 URL 추출

지원 URL:

~~~text
https://nol.yanolja.com/ticket/products/{concert_id}
~~~

검증 URL:

~~~text
https://nol.yanolja.com/ticket/products/26012624
~~~

---

## Phase 3. PaddleOCR

ImageTextExtractor를 구현한다.

사용 설정:

~~~python
PaddleOCR(
    lang="korean",
    ocr_version="PP-OCRv5",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
~~~

상세 이미지 다운로드 → PaddleOCR 실행 → 검색에 사용할 텍스트 반환 순서로 구현한다.

완료 조건: 팬클럽 인증, 선예매, 일반예매, 배송, 현장수령, 본인확인 중 여러 항목을 실제 이미지에서 읽을 수 있어야 한다.

---

## Phase 4. LangChain Document

HTML과 OCR 결과를 LangChain Document로 변환한다.

Metadata:

~~~json
{
  "concert_id": "26012624",
  "source_type": "html | image",
  "source_url": "...",
  "section": "..."
}
~~~

HTML과 OCR 원문을 보존하며 source_type을 유지한다.

---

## Phase 5. Text Splitter

긴 Document를 검색 가능한 Chunk로 분할한다.

초기 후보:

~~~text
chunk_size: 800~1200
chunk_overlap: 100~200
~~~

실제 공지로 테스트하여 값을 결정하고 제목과 안내 내용이 불필요하게 분리되지 않도록 한다.

---

## Phase 6. Embedding + Chroma

- OpenAI Embedding으로 Chunk를 Vector로 변환
- Chroma에 저장
- concert_id를 metadata에 저장
- 동일 공연이 이미 저장되어 있으면 OCR 및 Embedding 반복 금지

---

## Phase 7. Retriever

현재 URL의 concert_id로 검색 범위를 제한하고 질문과 관련된 Chunk를 가져온다.

초기 Top-K: 4~6

Retrieval 비교 질문:

~~~text
팬클럽 선예매하려면 언제 뭘 해야 해?
일반예매하고 현장에서 티켓 받을 건데 준비물이 뭐야?
배송은 언제 시작하고 현장수령은 언제부터 해야 해?
~~~

질문에 따라 서로 다른 Chunk가 검색되는지 확인한다.

---

## Phase 8. Query Understanding

복합 질문에서 사용자의 조건을 구조화한다.

예:

~~~json
{
  "booking_type": "fanclub_presale",
  "ticket_delivery": "onsite",
  "needed_topics": [
    "fanclub_verification",
    "presale",
    "onsite_pickup",
    "identity_verification"
  ]
}
~~~

단순 질문에서는 원본 질문만 사용한 Retrieval과 비교한다. 불필요한 LLM 호출이라고 판단되면 생략 가능하도록 설계한다.

---

## Phase 9. RAG Answer Chain

입력:
- 사용자 질문
- 질문 분석 결과
- Retriever Documents

Prompt 규칙:
- 검색된 Context만 예매 정보의 근거로 사용
- 없는 정보 추측 금지
- 날짜/시간/가격 임의 수정 금지
- 사용자에게 불필요한 정보 최소화
- OCR 문자를 임의로 추정하여 수정하지 않음

---

## Phase 10. Structured Output

응답 모델:

~~~python
class TicketGuideResponse(BaseModel):
    summary: str
    schedule: list[str]
    requirements: list[str]
    ticket_info: list[str]
    warnings: list[str]
    sources: list[str]
~~~

Structured Output 실패 시 한 번 재시도한다.

---

## Phase 11. FastAPI 통합

API:

~~~text
POST /api/guide
~~~

Request:

~~~json
{
  "url": "https://nol.yanolja.com/ticket/products/26012624",
  "question": "팬클럽 선예매 할 건데 언제 뭘 해야 해?"
}
~~~

처리 흐름:

~~~text
URL 검증
↓
concert_id 추출
↓
Index 존재 확인
↓
없으면 Ingestion
↓
Retriever
↓
RAG Chain
↓
Structured Output
~~~

---

## Phase 12. Vue 화면

단일 화면으로 구현한다.

입력: NOL Ticket URL, 사용자 질문
출력: 핵심 안내, 일정, 준비사항, 티켓 정보, 주의사항, 참고 근거

별도의 공연 분석 버튼은 만들지 않는다.

---

## Phase 13. 예외 처리

다음 상황을 처리한다.

~~~text
잘못된 URL
NOL Ticket이 아닌 URL
HTML 요청 실패
상세 이미지 없음
OCR 실패
Retriever 결과 없음
LLM 응답 실패
Structured Output Parsing 실패
~~~

OCR 실패 시 HTML Context만 이용하여 답변을 시도한다.
Retriever 결과가 없는 경우 LLM이 임의로 답변하지 않는다.

---

## Phase 14. 최종 테스트

동일 공연에 대해 최소 3개의 서로 다른 질문을 테스트한다.

1. MyDay 6기인데 선예매하려면 언제까지 인증해야 해?
2. 일반예매하고 현장에서 표 받을 건데 뭘 챙겨야 해?
3. 9월 30일에 예매하면 티켓 배송돼?

확인 항목:
- Retriever가 질문별로 다른 Context를 선택하는가
- 답변이 Context의 내용과 일치하는가
- 없는 정보를 생성하지 않는가
- 구조화된 결과가 정상적으로 반환되는가

추가 환각 테스트:

~~~text
팬클럽 회원이면 굿즈를 무료로 줘?
~~~

공지에 관련 내용이 없다면 예매 페이지에서 확인할 수 없다고 답해야 한다.
