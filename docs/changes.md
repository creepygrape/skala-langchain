# Implementation Change Log

구현 과정에서 기존 요구사항, 아키텍처 또는 기술 결정이 변경된 경우 기록한다.

단순 리팩터링, 변수명 변경, 오타 수정 등
설계에 영향을 주지 않는 변경은 기록하지 않는다.

---

## 기록 대상

다음과 같은 변경을 기록한다.

- 요구사항 변경
- 아키텍처 변경
- 기술 스택 변경
- API 계약 변경
- 데이터 구조 변경
- RAG / Retriever 전략 변경
- Chunk 전략 변경
- Prompt / Chain 구조 변경
- 기존 기술 검증 결과와 다른 구현 결정

---

## 기록 형식

### YYYY-MM-DD — 변경 제목

**기존**
- 기존 요구사항 또는 설계

**변경**
- 변경된 내용

**이유**
- 변경이 필요한 이유
- 테스트 또는 구현 과정에서 발견한 문제

**영향**
- 영향받는 문서
- 영향받는 코드 또는 기능

---

## Changes

### 2026-09-22 — 노트북 Retriever 하이브리드 검색 보완

**기존**
- `result.ipynb`가 Chroma 유사도 검색의 Top-5 결과를 그대로 사용
- HTML과 OCR의 검색 우선순위가 같아 OCR 중복·노이즈 Chunk가 결과를 차지할 수 있음

**변경**
- 벡터 검색 후보를 최대 10개로 확대하고 질문 분석 결과의 핵심어 직접 일치 후보를 함께 수집
- 문서 빈도를 반영한 핵심어 점수와 벡터 순위를 결합해 후보를 재정렬
- 배송·현장수령 의도의 정확 구문 점수를 추가하고 공백을 제거한 형태로 비교
- 핵심어가 일치한 HTML Chunk에 우선 점수를 부여하고 최종 OCR 결과를 최대 2개로 제한
- 질문의 전제를 부정하는 일반 정책은 직접 근거로 인정하고, 질문하지 않은 특정 좌석 전용 안내는 제외하도록 Evidence Filter 규칙 보완
- 검색 결과에 결합 점수, 벡터 순위, 일치 핵심어를 출력하도록 진단 정보 추가
- 노트북의 Chroma 셀 재실행 시 `concert_id` 존재 여부를 확인하여 같은 공연의 기존 Vector를 재사용하고, 다른 공연의 Vector는 함께 유지

**이유**
- `26012865` 공연의 배송 질문에서 실제 HTML에 "배송 및 현장 수령은 진행하지 않습니다"라는 근거가 있지만, 단순 유사도 Top-5에는 휠체어석·취소 안내 등 무관한 Chunk가 먼저 검색됨
- HTML 우선 규칙이 답변 Context 정렬에만 적용되고 검색 후보 선택에는 적용되지 않던 문제를 보완할 필요가 있음
- 같은 런타임에서 Vector Store 셀을 반복 실행하면 동일 Chunk가 누적되는 문제를 막으면서도, A 공연 → B 공연 → A 공연 순서에서는 기존 A Vector를 재사용할 필요가 있음

**영향**
- `result.ipynb`의 LangChain 시연용 Retriever 단계
- 기존 Backend Retriever 구현과 서비스 아키텍처는 변경하지 않음

### 2026-09-21 — Text Splitter 설정 확정

**기존**
- `chunk_size` 후보: 800~1200
- `chunk_overlap` 후보: 100~200
- 실제 공지를 이용한 검증 후 최종값 결정 예정

**변경**
- `RecursiveCharacterTextSplitter` 사용
- `chunk_size`: 1000
- `chunk_overlap`: 150
- 문단과 줄 경계를 우선하는 separator 적용
- 분할된 Chunk에 원본 metadata 유지

**이유**
- `26012624` 공연의 HTML 5,113자와 OCR 6,993자를 분할한 결과 21개 Chunk가 생성됐으며 최대 길이는 991자였음
- 팬클럽 인증, 선예매, 일반예매, 배송, 현장수령, 본인확인, 티켓 수령 안내가 관련 Chunk에 유지됨

**영향**
- `docs/architecture.md` Text Splitter 설정
- `backend/app/rag/document_processor.py` 문서 분할 로직

### 2026-09-21 — Embedding 모델 및 Vector Store 구성 확정

**기존**
- OpenAI Embedding과 Chroma 사용
- 구체적인 Embedding 모델과 Chroma 저장 방식은 미정

**변경**
- Embedding 모델: `text-embedding-3-small`
- Vector Store: 프로세스 메모리에서 동작하는 Chroma
- `concert_id` metadata를 기준으로 공연별 저장 여부 확인
- 이미 저장된 공연은 Document 추가와 Embedding을 생략

**이유**
- MVP에서는 영구 저장이 필수가 아니므로 별도 저장소 설정 없이 인메모리 Chroma로 기능 검증 가능
- OpenAI 공식 문서에서 `text-embedding-3-small`을 기본 소형 Embedding 모델로 제공함
- 실제 OpenAI Embedding 및 Chroma 저장 검증에서 공연별 존재 확인과 중복 저장 방지가 정상 동작함

**영향**
- `docs/architecture.md` Embedding / Chroma 설정
- `backend/app/rag/vector_store.py` Vector Store 관리
- `backend/requirements.txt` LangChain OpenAI / Chroma 통합 패키지

### 2026-09-21 — Retriever 검색 설정 확정

**기존**
- Retriever의 초기 `Top-K` 후보: 4~6
- 실제 공지를 이용한 검증 후 최종값 결정 예정

**변경**
- Chroma 유사도 검색 사용
- `Top-K`: 5
- 모든 검색에 현재 URL의 `concert_id` metadata filter 적용

**이유**
- `26012624` 공연의 21개 Chunk를 대상으로 세 가지 비교 질문을 검색한 결과, 팬클럽 인증·선예매, 현장수령·본인확인, 배송 일정에 해당하는 서로 다른 관련 Chunk가 Top-5 안에 검색됨
- 여러 공연을 같은 Vector Store에 저장한 테스트에서 요청한 `concert_id` 이외의 Chunk가 반환되지 않음을 확인함

**영향**
- `docs/architecture.md` Retriever 설정
- `backend/app/rag/vector_store.py` 공연별 Retriever 생성 및 검색 로직

### 2026-09-21 — 구현 순서 문서 단일화

**기존**
- `docs/tasks.md`와 `docs/architecture.md`가 서로 다른 Phase 번호로 구현 순서를 중복 관리함

**변경**
- 구현 순서는 `docs/tasks.md`에서만 관리
- `docs/architecture.md`의 중복된 구현 순서 절 제거

**이유**
- 서로 다른 Phase 번호로 인해 현재 구현 단계가 혼동됨

**영향**
- `docs/architecture.md` 이후 절 번호 조정

### 2026-09-21 — Query Understanding 실행 전략 확정

**기존**
- 복합 질문의 조건을 구조화하되 단순 질문에서는 생략 가능
- 구체적인 생략 기준과 Chat 모델은 미정

**변경**
- 서로 다른 정보 주제가 두 개 이상 포함된 질문만 Query Understanding 실행
- 단일 주제 질문은 LLM 호출 없이 원문 질문을 검색어로 사용
- 복합 질문은 원문과 구조화된 검색 핵심어를 결합
- Structured Output 모델: `gpt-4o-mini`

**이유**
- 단일 주제 질문은 원문만으로 관련 Chunk 검색이 가능해 추가 LLM 호출이 불필요함
- 복합 질문은 예매 유형, 수령 방식, 필요한 주제를 명시해 검색 범위를 보완할 수 있음
- OpenAI 공식 문서에서 `gpt-4o-mini`는 집중된 작업에 적합한 소형 모델이며 Structured Output을 지원함

**영향**
- `docs/architecture.md` Query Understanding 설정
- `backend/app/rag/query_analyzer.py` 질문 분석 및 검색어 생성 로직
