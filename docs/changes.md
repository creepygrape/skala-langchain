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
