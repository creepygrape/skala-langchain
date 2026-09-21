# 맞춤형 콘서트 예매 가이드

## 개발 환경 실행

Backend:

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

Frontend (별도 터미널):

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 열면 Backend 연결 상태를 확인할 수 있다.
