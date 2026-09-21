# 맞춤형 콘서트 예매 가이드 — Architecture

## 1. 문서 목적

본 문서는 `requirements.md`에 정의된 **맞춤형 콘서트 예매 가이드**의 MVP 아키텍처를 정의한다.

서비스의 핵심은 예매 페이지 전체를 단순 요약하는 것이 아니라,

1. 예매 페이지의 HTML 및 상세 이미지 정보를 수집하고
2. 검색 가능한 문서로 변환한 뒤
3. 사용자의 질문과 관련된 Context만 검색하고
4. LLM이 해당 Context를 근거로 맞춤형 답변을 생성하는 것이다.

사용자에게는 **URL + 질문 → 답변**의 단순한 흐름만 제공하되,
백엔드 내부에서는 문서 수집(Ingestion)과 질의응답(QA)을 분리한다.

---

## 2. 기술 스택

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | Vue | URL/질문 입력 및 결과 화면 |
| Backend | FastAPI | Vue 요청 처리 및 LangChain 호출 |
| AI Framework | LangChain | Loader, Retriever, Prompt, Chain, Output 구성 |
| LLM | OpenAI Chat Model | 질문 해석 및 최종 답변 생성 |
| Embedding | OpenAI Embedding | 문서와 질문을 Vector로 변환 |
| Vector Store | Chroma | 예매 공지 Vector 저장 및 의미 기반 검색 |
| OCR | PaddleOCR (PP-OCRv5, Korean) | 상세 공지 이미지의 한국어 텍스트 추출 |
| HTML Parsing | requests + BeautifulSoup | NOL Ticket HTML 텍스트 및 상세 이미지 URL 추출 |

---

## 3. 전체 시스템 구조

```text
┌──────────────────────────────────────┐
│                 Vue                  │
│                                      │
│  - NOL Ticket URL 입력               │
│  - 사용자 질문 입력                  │
│  - 맞춤형 예매 결과 출력             │
└─────────────────┬────────────────────┘
                  │ HTTP / JSON
                  ▼
┌──────────────────────────────────────┐
│              FastAPI                 │
│                                      │
│            POST /api/guide           │
└─────────────────┬────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│         TicketGuideService           │
│                                      │
│  - URL 검증                          │
│  - 공연 인덱스 존재 여부 확인        │
│  - 필요 시 Ingestion 실행            │
│  - QA Pipeline 실행                  │
└───────────┬──────────────────────────┘
            │
     ┌──────┴─────────────┐
     │                    │
     ▼                    ▼
┌───────────────┐   ┌──────────────────┐
│   Ingestion   │   │    QA Pipeline   │
│   Pipeline    │   │                  │
└──────┬────────┘   └────────┬─────────┘
       │                     │
       ▼                     ▼
 HTML Loader          Query Understanding
       │                     │
       ├── Image URL         ▼
       │    Extractor      Retriever
       │       │             │
       │       ▼             ▼
       │   PaddleOCR    Relevant Context
       │       │             │
       └───┬───┘             ▼
           ▼             Prompt Template
     LangChain Document      │
           │                 ▼
           ▼                LLM
      Text Splitter           │
           │                 ▼
           ▼          Structured Output
       Embedding              │
           │                 ▼
           ▼            JSON Response
        Chroma
```

---

## 4. 핵심 설계 원칙

### 4.1 사용자에게는 URL + 질문만 받는다

사용자는 공연 정보를 먼저 분석한 뒤 질문하는 두 단계 흐름을 거치지 않는다.

한 화면에서 다음 두 값만 입력한다.

```text
예매 URL
+
사용자 질문
```

예:

```text
URL:
https://nol.yanolja.com/ticket/products/26012624

질문:
팬클럽 선예매인데 현장수령이면 뭐 준비해야 해?
```

사용자는 내부적으로 문서 수집, OCR, Embedding, Vector Store 생성이 수행되는지 알 필요가 없다.

---

### 4.2 내부적으로는 문서 수집과 질의응답을 분리한다

사용자 입력은 한 번에 받지만, 백엔드에서는 다음 두 Pipeline을 분리한다.

```text
1. Document Ingestion Pipeline
2. Question Answering Pipeline
```

같은 공연 URL이 이미 분석되어 있다면 다시 HTML 수집, OCR, Embedding을 수행하지 않고 기존 Chroma 데이터를 재사용한다.

```text
URL + Question
      │
      ▼
concert_id 추출
      │
      ▼
Vector Store에 해당 공연 데이터 존재?
      │
   ┌──┴──┐
   │     │
  NO    YES
   │     │
   ▼     │
Ingestion│
   │     │
   └──┬──┘
      ▼
QA Pipeline
```

---

### 4.3 전체 공지를 LLM에 넣지 않는다

예매 공지가 매우 길더라도 전체 내용을 Prompt에 넣지 않는다.

Retriever가 현재 질문과 관련 있는 Chunk만 검색한다.

예:

```text
질문:
"팬클럽 선예매 전에 해야 할 게 뭐야?"
```

Retriever 결과:

```text
1. 팬클럽 인증 안내
2. 선예매 일정
3. 팬클럽 인증 주의사항
```

배송, 취소, 휠체어석 등 현재 질문과 관계없는 Context는 제외한다.

---

### 4.4 LLM은 공지를 생성하지 않고 해석한다

LLM은 자신의 사전 지식으로 공연 정보를 답변하지 않는다.

최종 답변은 반드시 다음 정보를 근거로 한다.

```text
사용자 질문
+
Retriever가 검색한 예매 공지
```

공지에서 찾을 수 없는 내용은 추측하지 않는다.

---

## 5. API 흐름

MVP에서는 사용자 관점의 API를 하나로 단순화한다.

### POST /api/guide

#### Request

```json
{
  "url": "https://nol.yanolja.com/ticket/products/26012624",
  "question": "팬클럽 선예매인데 현장수령이면 뭐 준비해야 해?"
}
```

#### Backend 처리

```text
URL + Question
      │
      ▼
URL Validation
      │
      ▼
concert_id 추출
      │
      ▼
해당 공연 Vector Index 존재 여부 확인
      │
   ┌──┴──┐
   │     │
  NO    YES
   │     │
   ▼     │
HTML + OCR
   │
Document
   │
Split + Embedding
   │
Chroma 저장
   │
   └─────┬───────────────┘
         ▼
Query Understanding
         │
         ▼
Retriever
         │
         ▼
Relevant Context
         │
         ▼
Prompt Template
         │
         ▼
LLM
         │
         ▼
Structured Output
```

#### Response

```json
{
  "summary": "...",
  "schedule": [],
  "requirements": [],
  "ticket_info": [],
  "warnings": [],
  "sources": []
}
```

---

## 6. Document Ingestion Pipeline

### 목적

NOL Ticket 예매 페이지를 LangChain에서 검색 가능한 Document로 변환한다.

### 흐름

```text
NOL Ticket URL
      │
      ▼
URL Validation
      │
      ▼
HTML Request
      │
      ├──────────────┐
      ▼              ▼
HTML Text       Detail Image URL
      │              │
      │              ▼
      │         Image Download
      │              │
      │              ▼
      │          PaddleOCR
      │              │
      ▼              ▼
HTML Document   Image Document
      │              │
      └──────┬───────┘
             ▼
      Document Merge
             │
             ▼
        Text Splitter
             │
             ▼
          Embedding
             │
             ▼
           Chroma
```

---

## 7. URL Validation

입력받은 URL이 MVP에서 지원하는 NOL Ticket 상품 페이지인지 확인한다.

지원 예:

```text
https://nol.yanolja.com/ticket/products/26012624
```

검증 항목:

- URL 형식
- Domain
- `/ticket/products/{id}` 형태
- 실제 페이지 접근 가능 여부

상품 ID를 `concert_id`로 사용한다.

예:

```text
26012624
```

---

## 8. HTML Loader

### 역할

NOL Ticket 상품 페이지에서 HTML 텍스트를 수집한다.

수집 대상 예:

- 공연명
- 공연 장소
- 공연 기간
- 좌석 가격
- 공연 시간
- 티켓 배송 정보
- 취소/환불 정책
- 기타 텍스트 안내

### 구현 방법

기술 검증 결과 NOL Ticket 상품 페이지는 브라우저 자동화 없이 일반 HTTP 요청으로 필요한 정보를 수집할 수 있었다.

MVP에서는 다음 구성을 사용한다.

```text
requests
+
BeautifulSoup
```

HTML에서 공연 기본 정보와 상세 공지 이미지 URL을 추출한다.

---

## 9. 상세 이미지 탐지 및 PaddleOCR

예매 페이지의 HTML에서 상품 상세 공지 이미지 URL을 탐지한다.

상세 이미지에는 다음 정보가 포함될 수 있다.

- 팬클럽 인증
- 팬클럽 선예매
- 일반예매
- 티켓 매수 제한
- 본인확인
- 현장수령
- 공연 입장 안내
- 기타 주의사항

처리 흐름:

```text
상세 이미지
↓
PaddleOCR
↓
추출된 Text
↓
LangChain Document
```

PaddleOCR 선정 이유:

- 오픈소스
- 로컬 실행 가능
- 별도의 OCR API 호출 비용 없음
- 한국어 텍스트 처리 가능

### 9.1 OCR 설정

MVP에서는 다음 설정을 사용한다.

```python
PaddleOCR(
    lang="korean",
    ocr_version="PP-OCRv5",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
```

기술 검증에서 한국어 모델을 지정하지 않은 경우 영어와 숫자는 일부 인식되었으나 한국어 본문 인식률이 매우 낮았다.

`lang="korean"`과 `PP-OCRv5`를 적용한 뒤 팬클럽 인증, 선예매, 일반예매, 본인확인, 배송, 현장수령 등 핵심 정보를 추출할 수 있었다.

OCR 품질이 부족한 경우 이미지 분할·확대 또는 Vision LLM 적용을 향후 개선 방향으로 둔다.

### 9.2 데이터 신뢰 우선순위

HTML과 상세 이미지 OCR에 동일한 정보가 존재할 수 있다.

중복 정보가 존재하는 경우 다음 우선순위를 적용한다.

```text
HTML
↓
OCR
```

HTML은 OCR 과정의 문자 인식 오류가 없으므로 동일 정보에 대해서는 HTML 원문을 우선한다.

OCR은 HTML에 존재하지 않는 상세 공지를 보완한다.

OCR 결과에는 다음과 같은 오류가 발생할 수 있다.

```text
NOL → N이L / N으L
ID → 1D
숫자 및 띄어쓰기 일부 오인식
```

따라서 날짜, 시간, 가격 등의 값을 애플리케이션에서 임의로 보정하지 않는다.

각 Document에는 원문과 출처 metadata를 함께 보존하며, 최종 답변 생성 시 Retriever가 가져온 원문 Context를 LLM에 전달한다.

---

## 10. LangChain Document

HTML과 OCR 결과는 모두 LangChain `Document` 형태로 통일한다.

예:

```python
Document(
    page_content="팬클럽 선예매는 ...",
    metadata={
        "concert_id": "26012624",
        "source_type": "image",
        "source_url": "...",
        "section": "presale"
    }
)
```

### Metadata

| 필드 | 설명 |
|---|---|
| `concert_id` | NOL Ticket 상품 ID |
| `source_type` | html / image |
| `source_url` | 원본 페이지 또는 이미지 URL |
| `section` | 문서 내용 분류 |

section 예:

```text
basic_info
fanclub_verification
presale
general_sale
ticket_delivery
onsite_pickup
identity_verification
cancellation
admission
notice
unknown
```

---

## 11. Text Splitter

긴 공지를 Retriever가 검색하기 적절한 크기의 Chunk로 분할한다.

단순히 문자를 일정 길이마다 자르지 않고 가능한 한 하나의 안내 사항을 함께 유지한다.

MVP 설정:

```text
Text Splitter: RecursiveCharacterTextSplitter
chunk_size: 1000
chunk_overlap: 150
```

문단과 줄 경계를 문자 경계보다 우선하여 분할하고, 각 Chunk에는 원본 Document의 metadata를 유지한다.

실제 `26012624` 공연의 HTML 및 OCR 문서로 검증한 결과 최대 Chunk 길이는 991자였으며, 팬클럽 인증·선예매·일반예매·배송·현장수령·본인확인 안내가 관련 Chunk에 유지됐다.

---

## 12. Embedding / Chroma

### Embedding

공지 Chunk를 의미를 표현하는 Vector로 변환한다.

문자열이 정확히 일치하지 않아도 의미적으로 비슷한 내용을 검색할 수 있도록 한다.

MVP에서는 OpenAI `text-embedding-3-small` 모델을 사용한다.

### Chroma

Embedding된 콘서트 공지 Chunk를 저장하고 검색한다.

공연별 `concert_id`를 metadata로 저장하여 동일 Vector Store 안에서도 공연별 검색 범위를 구분한다.

예:

```text
concert_id = 26012624
```

질문 시 해당 공연의 Chunk만 대상으로 Retrieval한다.

MVP Vector Store는 프로세스 메모리에서 동작한다. 동일한 `concert_id`의 Chunk가 이미 존재하면 Ingestion과 Embedding을 다시 수행하지 않도록 존재 여부를 먼저 확인한다.

---

## 13. Question Answering Pipeline

사용자 질문이 들어오면 실행되는 Pipeline이다.

```text
User Question
      │
      ▼
Query Understanding
      │
      ▼
Search Query
      │
      ▼
Retriever
      │
      ▼
Relevant Documents
      │
      ▼
Prompt Template
      │
      ▼
LLM
      │
      ▼
Structured Output
```

---

## 14. Query Understanding Chain

### 목적

사용자가 자연스럽게 입력한 질문에서 필요한 정보 주제를 파악한다.

예:

```text
팬클럽 선예매 할 거고
현장수령 예정인데 언제 뭘 해야 해?
```

분석 결과:

```json
{
  "booking_type": "fanclub_presale",
  "ticket_delivery": "onsite",
  "needed_topics": [
    "fanclub_verification",
    "presale",
    "onsite_pickup",
    "identity_verification"
  ],
  "search_query": "팬클럽 인증 선예매 현장수령 본인확인"
}
```

단순 질문에서는 원본 질문을 그대로 Retrieval에 사용할 수 있다.

Query Understanding이 불필요한 LLM 호출을 발생시키는 경우에는 생략할 수 있도록 한다.

MVP에서는 질문에 서로 다른 정보 주제가 두 개 이상 포함된 경우에만 Query Understanding을 실행한다. 단일 주제 질문은 원문을 그대로 검색하며, 복합 질문은 원문과 구조화된 검색 핵심어를 함께 사용한다.

Query Understanding에는 OpenAI `gpt-4o-mini`의 Structured Output을 사용한다.

---

## 15. Retriever

사용자 질문과 관련 있는 Chunk를 Chroma에서 가져온다.

검색 시 `concert_id`로 필터링하여 사용자가 입력한 공연의 Document만 대상으로 한다.

MVP 설정:

```text
Search: similarity
Top-K: 5
Filter: concert_id
```

`26012624` 공연의 21개 Chunk를 대상으로 팬클럽 선예매, 일반예매 후 현장수령 준비물, 배송 및 현장수령 일정 질문을 비교한 결과, 각 질문에서 서로 다른 관련 Chunk가 Top-5 안에 검색됐다.

---

## 16. 최종 Prompt 구성

LLM에 전달되는 Context는 다음 구조로 통일한다.

```text
[ROLE]

너는 콘서트 예매 정보를 안내하는 AI 도우미다.


[USER QUESTION]

팬클럽 선예매 할 거고
현장수령 예정인데 언제 뭘 해야 해?


[USER CONTEXT]

booking_type: fanclub_presale
ticket_delivery: onsite


[REFERENCE DOCUMENTS]

Document 1 ...
Document 2 ...
Document 3 ...


[RULES]

- Reference Documents만 예매 정보의 근거로 사용
- 없는 정보 추측 금지
- 날짜 및 시간 임의 수정 금지
- 사용자와 관련 없는 정보 최소화
- 중요한 제한사항 생략 금지


[OUTPUT]

summary
schedule
requirements
ticket_info
warnings
sources
```

---

## 17. Structured Output

LLM의 최종 응답은 자유로운 문자열 대신 일정한 JSON 구조로 반환한다.

```python
class TicketGuideResponse(BaseModel):
    summary: str
    schedule: list[str]
    requirements: list[str]
    ticket_info: list[str]
    warnings: list[str]
    sources: list[str]
```

---

## 18. Vue 화면 구조

MVP는 단일 화면으로 구성한다.

```text
┌──────────────────────────────────────────┐
│        맞춤형 콘서트 예매 가이드        │
├──────────────────────────────────────────┤
│                                          │
│ 예매 URL                                 │
│ [                                     ]  │
│                                          │
│ 궁금한 내용을 입력하세요                │
│ [                                     ]  │
│ [                                     ]  │
│                                          │
│ [ 맞춤형 예매 정보 확인 ]               │
│                                          │
├──────────────────────────────────────────┤
│ 핵심 안내                                │
│ 일정                                     │
│ 준비사항                                 │
│ 티켓 정보                                │
│ 주의사항                                 │
│ 참고 근거                                │
└──────────────────────────────────────────┘
```

사용자에게 별도의 "공연 정보 불러오기" 단계를 노출하지 않는다.

---

## 19. Frontend 책임

Vue에서는 다음만 담당한다.

- URL 입력
- 질문 입력
- `POST /api/guide` 호출
- Loading 표시
- 오류 메시지 표시
- 결과 화면 출력

다음 기능은 Vue에서 구현하지 않는다.

- 페이지 Crawling
- OCR
- Embedding
- Vector 검색
- Prompt 구성
- LLM 호출

모든 AI 로직은 Backend에서 담당한다.

---

## 20. Backend 주요 클래스 책임

### TicketGuideService

전체 서비스 흐름을 조율한다.

책임:

- URL 검증
- concert_id 추출
- 해당 공연 Vector Index 존재 여부 확인
- 필요 시 Ingestion Pipeline 실행
- Query Understanding 실행
- Retrieval 실행
- Answer Chain 실행
- 결과 반환

### NolTicketLoader

책임:

- NOL Ticket URL 접근
- HTML 텍스트 수집
- 상세 이미지 URL 탐색

### ImageTextExtractor

책임:

- 상세 이미지 다운로드
- PaddleOCR 실행
- OCR 결과 텍스트 반환

### DocumentProcessor

책임:

- HTML Document 생성
- OCR Document 생성
- Metadata 설정
- Document 통합
- Text Split

### VectorStoreService

책임:

- Embedding 생성
- Chroma 저장
- 공연별 index 존재 여부 확인
- concert_id 기반 Retriever 제공

### QueryAnalyzer

책임:

- 사용자 질문 분석
- 필요한 Topic 추출
- Retrieval 검색 Query 생성

### TicketGuideChain

책임:

- 검색 Document와 사용자 질문을 Prompt로 구성
- OpenAI 호출
- Structured Output 반환

---

## 21. 디렉터리 구조

```text
skala-langchain/
│
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   ├── technical-validation.md
│   └── tasks.md
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── ticketGuideApi.js
│   │   ├── components/
│   │   │   ├── UrlInput.vue
│   │   │   ├── QuestionInput.vue
│   │   │   └── GuideResult.vue
│   │   ├── views/
│   │   │   └── TicketGuideView.vue
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── ticket_guide.py
│   │   ├── chains/
│   │   │   ├── query_analysis_chain.py
│   │   │   └── ticket_guide_chain.py
│   │   ├── loaders/
│   │   │   ├── nol_ticket_loader.py
│   │   │   └── image_text_extractor.py
│   │   ├── rag/
│   │   │   ├── document_processor.py
│   │   │   └── vector_store.py
│   │   ├── models/
│   │   │   ├── query_analysis.py
│   │   │   └── ticket_guide_response.py
│   │   ├── prompts/
│   │   │   ├── query_analysis_prompt.py
│   │   │   └── ticket_guide_prompt.py
│   │   └── services/
│   │       └── ticket_guide_service.py
│   └── requirements.txt
│
├── tests/
│   ├── test_loader.py
│   ├── test_ocr.py
│   ├── test_retrieval.py
│   └── test_ticket_guide.py
│
├── .env.example
└── README.md
```

---

## 22. 환경 변수

API Key는 코드에 직접 작성하지 않는다.

`.env`

```text
OPENAI_API_KEY=
```

`.env.example`

```text
OPENAI_API_KEY=your_api_key
```

`.env`는 Git에 Commit하지 않는다.

---

## 23. 예외 처리

### HTML 수집 실패

```text
예매 페이지를 불러올 수 없습니다.
URL을 확인해주세요.
```

Pipeline 종료.

### OCR 실패

HTML Document는 그대로 사용한다.

응답 Warning:

```text
상세 공지 이미지 분석에 실패해
일부 안내가 누락되었을 수 있습니다.
```

### Retriever 결과 없음

LLM에게 빈 Context를 보내 임의 답변을 생성하지 않는다.

```text
예매 페이지에서 질문과 관련된 정보를 확인하지 못했습니다.
```

### Structured Output Parsing 실패

1회 재시도한다.

재시도 후에도 실패하면 AI 처리 오류로 반환한다.

---

## 24. 테스트 전략

### Loader Test

- NOL Ticket HTML을 정상 수집하는가
- 공연명/날짜/가격 등의 텍스트를 가져오는가
- 상세 이미지 URL을 찾는가

### OCR Test

실제 NOL Ticket 상세 이미지로 다음을 확인한다.

- 날짜
- 시간
- 숫자
- 팬클럽 인증
- 선예매
- 본인확인

### Retrieval Test

질문별로 검색 Context가 달라지는지 확인한다.

예:

```text
팬클럽 선예매 언제야?
→ 팬클럽 인증 / 선예매 일정
```

```text
현장에서 표 받을 때 뭐 필요해?
→ 현장수령 / 본인확인
```

```text
취소 수수료 알려줘.
→ 취소 / 환불 / 수수료
```

### Cache Reuse Test

같은 URL로 연속 질문할 때 두 번째 질문부터는 HTML 수집, OCR, Embedding을 다시 수행하지 않는지 확인한다.

### Hallucination Test

질문:

```text
팬클럽 회원이면 콘서트 굿즈 무료로 줘?
```

공지에 해당 내용이 없다면:

```text
예매 페이지에서 확인할 수 없습니다.
```

를 반환해야 한다.

---

## 25. LangChain 컴포넌트 사용 이유

| Component | 역할 | 사용 이유 | 없을 경우 |
|---|---|---|---|
| Document | 수집 정보 통일 | HTML/OCR 결과를 동일한 형태로 관리 | 데이터 처리 방식이 분리됨 |
| Document Loader | HTML 수집 | 웹 내용을 LangChain 처리 대상으로 변환 | 직접 변환 로직 필요 |
| Text Splitter | 문서 분할 | 관련 Context만 검색하기 위해 | 너무 긴 문서 전체가 검색됨 |
| Embedding | 의미 Vector화 | 표현이 다른 문장도 의미 기반 검색 | 정확한 키워드 의존 |
| Chroma | Vector Store | Chunk 저장 및 유사도 검색 | 매 질문마다 전체 문서 비교 |
| Retriever | Context 선택 | 현재 질문에 필요한 내용만 선택 | 전체 공지를 Prompt에 넣어야 함 |
| Prompt Template | Context 구성 | 모델 입력 형식과 제약을 일관되게 유지 | 호출마다 입력 구조가 달라짐 |
| Structured Output | 출력 통일 | Vue에서 결과를 안정적으로 표시 | 자연어 응답을 다시 Parsing해야 함 |
| Chain | 단계 연결 | 질문 분석 → 검색 → 답변 생성 흐름 구성 | 각 AI 단계가 하나의 코드에 뒤섞임 |

---

## 26. 최종 처리 구조

```text
                    [사용자 입력]
                  URL + Question
                         │
                         ▼
                      FastAPI
                         │
                         ▼
                 URL Validation
                         │
                         ▼
                 concert_id 추출
                         │
                         ▼
             기존 Vector Index 존재?
                  /                \
                NO                 YES
                 │                  │
                 ▼                  │
          Ingestion Pipeline        │
       HTML + PaddleOCR             │
                 │                  │
              Document              │
                 │                  │
        Split + Embedding            │
                 │                  │
               Chroma ◀─────────────┘
                 │
                 ▼
        Query Understanding
                 │
                 ▼
              Retriever
                 │
                 ▼
         Relevant Context
                 │
                 ▼
          Prompt Template
                 │
                 ▼
            OpenAI LLM
                 │
                 ▼
        Structured Output
                 │
                 ▼
                Vue
```

---

## 27. 핵심 아키텍처 목표

본 프로젝트는 사용자에게 복잡한 내부 절차를 노출하지 않는다.

사용자는 단순히

```text
URL + 질문
→ 맞춤형 답변
```

만 경험한다.

내부적으로는 같은 공연 페이지를 반복 분석하지 않도록 Ingestion과 QA를 분리하고,
사용자 질문에 필요한 Context만 Retriever로 선택해 LLM에 전달한다.

즉,

> **UI/API는 단순하게, 내부 AI Pipeline은 역할별로 분리한다.**
