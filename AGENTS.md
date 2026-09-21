# AGENTS.md

## Before coding

작업 전에 반드시 다음 문서를 읽는다.

1. `docs/requirements.md`
2. `docs/architecture.md`
3. `docs/technical-validation.md`
4. `docs/tasks.md`
5. `docs/changes.md`

문서에 정의되지 않은 기능을 임의로 추가하지 않는다.

문서 간 충돌이나 설계 변경이 필요한 경우
임의로 결정하지 말고 사용자에게 확인한다.

## Workflow

`docs/tasks.md`의 Phase 순서대로 구현한다.

각 Phase마다 다음 순서를 따른다.

1. 구현
2. 테스트
3. 결과 확인
4. 실패 수정
5. 완료 내용 보고

사용자 확인 없이 다음 Phase로 넘어가지 않는다.

## Project constraints

- Frontend: Vue + Vite
- Backend: FastAPI
- HTML: requests + BeautifulSoup
- OCR: PaddleOCR (`lang="korean"`, `PP-OCRv5`)
- RAG: LangChain + OpenAI Embedding + Chroma
- LLM: OpenAI Chat Model

기존 기술 결정을 임의로 교체하지 않는다.

## Data rules

- 동일 정보가 HTML과 OCR에 있으면 HTML을 우선한다.
- OCR의 날짜, 시간, 가격 등을 추측하여 수정하지 않는다.
- 원문과 source metadata를 보존한다.
- Retriever Context에 없는 공연 정보는 생성하지 않는다.

## Change management

구현 과정에서 기존 요구사항, 아키텍처 또는 기술 결정과
달라지는 사항이 생기면 사용자에게 먼저 설명한다.

승인된 변경사항은 `docs/changes.md`에 기록한다.

필요한 경우 관련 원본 문서도 함께 수정한다.

## Validation

완료 보고에는 다음을 포함한다.

- 변경 파일
- 구현 내용
- 실행한 테스트
- 테스트 결과
- 남은 문제

테스트하지 않은 항목을 성공했다고 보고하지 않는다.

## Git

Commit message는 다음 형식을 사용한다.

`<type>: <summary>`

type:
`feat`, `fix`, `docs`, `test`, `refactor`, `chore`

하나의 Commit에는 하나의 목적만 포함한다.

Commit 또는 Push 전에 테스트 결과와 변경 내용을 사용자에게 보고한다.

사용자의 명시적인 승인 없이 Commit 또는 Push하지 않는다.
