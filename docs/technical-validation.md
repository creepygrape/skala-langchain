# 맞춤형 콘서트 예매 가이드 — Technical Validation

## 1. 목적

본 문서는 NOL Ticket 상품 페이지를 대상으로 HTML 수집과 상세 공지 이미지 OCR이 실제로 가능한지 검증한 결과를 기록한다.

서비스 구현 전 다음 항목을 확인했다.

- 일반 HTTP 요청으로 NOL Ticket 상품 페이지에 접근 가능한가
- HTML에서 공연 기본 정보를 추출할 수 있는가
- 상세 공지 이미지 URL을 추출할 수 있는가
- 상세 이미지의 한국어 안내문을 OCR로 읽을 수 있는가

---

## 2. HTML 수집 검증

### 테스트 대상

~~~text
https://nol.yanolja.com/ticket/products/26012479
https://nol.yanolja.com/ticket/products/26012624
~~~

### 테스트 방법

Python의 requests를 이용해 페이지 HTML을 요청하고, BeautifulSoup으로 HTML 텍스트와 이미지 URL을 추출했다.

### 결과

두 페이지 모두 HTTP 200 응답을 확인했다.

HTML에서 다음 정보를 직접 추출할 수 있었다.

~~~text
공연명
공연 장소
공연 기간
공연 시간
티켓 가격
예매 가능 시간
티켓 배송 정보
취소 및 환불 규정
일부 예매 안내
~~~

또한 ticketimage.interpark.com에 저장된 상품 상세 공지 이미지 URL을 HTML에서 탐지할 수 있었다.

### 결정

NOL Ticket MVP에서는 별도의 브라우저 자동화 도구 없이 requests + BeautifulSoup을 이용하여 페이지 데이터를 수집한다.

JavaScript 렌더링 문제로 정보 수집이 불가능한 페이지가 발견되는 경우에만 Playwright 등의 도입을 검토한다.

---

## 3. PaddleOCR 검증

### 초기 테스트

상세 공지 이미지를 PaddleOCR로 분석했다.

초기 설정에서는 영어와 숫자는 비교적 잘 인식했지만 한국어 본문의 상당 부분이 정상적으로 인식되지 않았다.

예를 들어 VIP198,000, R165,000 등은 인식되었으나 한국어 문장은 공백이나 잘못된 문자로 출력됐다.

### 원인

초기 OCR 실행 시 한국어 인식 모델을 명시하지 않았다.

### 개선

다음과 같이 한국어 모델을 명시했다.

~~~python
PaddleOCR(
    lang="korean",
    ocr_version="PP-OCRv5",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
~~~

### 개선 결과

한국어 모델 적용 후 다음 정보들을 읽을 수 있었다.

~~~text
팬클럽 인증 기간
팬클럽 선예매 일정
일반예매 일정
티켓 매수 제한
본인확인 안내
티켓 배송 일정
현장수령 조건
공연 입장 안내
공연장 안내
~~~

두 개의 서로 다른 NOL Ticket 공연 상세 이미지에서 동일한 방식으로 핵심 예매 정보 추출에 성공했다.

---

## 4. OCR 한계

OCR 결과가 항상 원문과 완전히 동일하지는 않았다.

대표적인 오류:

~~~text
NOL → N이L / N으L
ID → 1D
페이지 → 페OI지
현장 → 현징
12:00PM → 12:0OPM
~~~

띄어쓰기가 제거되는 경우도 있었다.

특히 전화번호, 날짜, 시간과 같은 숫자 정보에도 오인식 가능성이 있으므로 주의가 필요하다.

---

## 5. 데이터 신뢰 우선순위

HTML과 OCR에 동일한 정보가 존재하는 경우 OCR보다 HTML 데이터를 우선 사용한다.

~~~text
1순위: HTML 원문
2순위: 상세 이미지 OCR
~~~

OCR은 HTML에 존재하지 않는 상세 공지를 보완하는 역할로 사용한다.

OCR 결과를 임의로 수정하지 않고 원문과 출처 정보를 함께 LangChain Document에 저장한다.

---

## 6. 최종 기술 결정

### HTML

~~~text
requests + BeautifulSoup
~~~

### 이미지

~~~text
PaddleOCR
lang="korean"
PP-OCRv5
~~~

### 결론

NOL Ticket 상품 페이지의 HTML 정보와 상세 공지 이미지를 모두 텍스트화할 수 있음을 확인했다.

따라서 다음 단계에서는 수집 결과를 LangChain Document로 변환하고, Text Splitter → Embedding → Chroma → Retriever 흐름을 구현한다.

---

## 7. 향후 개선 가능성

현재 OCR 품질로 MVP 구현은 가능하다.

다만 매우 작은 글씨, 복잡한 표, 숫자 오인식, OCR 문장 순서 오류가 반복될 경우 개선을 검토한다.

개선 후보:

~~~text
이미지 구간 분할
이미지 확대 및 전처리
OCR confidence 활용
Vision LLM을 이용한 보조 분석
~~~

MVP에서는 과도한 OCR 전처리보다 현재 결과를 이용한 RAG 동작 검증을 우선한다.

---

## 8. 최종 RAG 검증

### 테스트 대상

~~~text
https://nol.yanolja.com/ticket/products/26012624
~~~

동일 공연을 한 번 수집해 21개 Chunk로 인덱싱한 뒤 서로 다른 질문을 연속 실행했다. HTML 수집과 OCR은 각각 한 번만 실행됐으며 이후 질문에서는 기존 인덱스를 재사용했다.

### 질문별 결과

1. MyDay 6기 선예매 인증 질문
   - 팬클럽 인증 기간과 선예매 안내 Chunk 검색
   - HTML 원문의 인증 마감 시각을 반영한 구조화 응답 반환
2. 일반예매 후 현장수령 준비물 질문
   - 현장수령 및 본인확인 Chunk 검색
   - 실물 신분증과 NOL 예매내역서 준비사항 반환
3. 9월 30일 예매 건의 배송 질문
   - 배송 및 현장수령 전환 기준 Chunk 검색
   - HTML 기준인 9월 28일 10:00AM 이후 현장수령 안내 반환
4. 팬클럽 회원의 무료 굿즈 질문
   - 공지에 직접 근거가 없으므로 `예매 페이지에서 확인할 수 없습니다.` 반환
   - 관련 없는 상세 목록은 비워 환각성 부가정보를 차단

### 확인 결과

- 질문에 따라 서로 다른 Context가 검색됨
- HTML과 OCR의 시간이 충돌하는 경우 HTML 값을 우선함
- 모든 응답이 `TicketGuideResponse` 구조로 반환됨
- 같은 공연에 대한 HTML, OCR, Embedding 반복을 방지함
- 공지에 없는 무료 굿즈 정보를 생성하지 않음
