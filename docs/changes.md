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
