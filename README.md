# 맞춤형 콘서트 예매 가이드

## 개발 환경 실행

### Backend

프로젝트 루트 디렉터리에서 실행합니다.

#### Windows (PowerShell)

최초 실행 시:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

Copy-Item .env.example .env
# .env 파일의 OPENAI_API_KEY에 실제 API Key 입력

pip install -r backend\requirements-dev.txt

cd backend
python -m uvicorn app.main:app --reload --env-file ../.env
```

이후 실행 시:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --env-file ../.env
```

#### macOS / Linux

최초 실행 시:

```bash
python3 -m venv .venv
source .venv/bin/activate

cp .env.example .env
# .env 파일의 OPENAI_API_KEY에 실제 API Key 입력

pip install -r backend/requirements-dev.txt

cd backend
python -m uvicorn app.main:app --reload --env-file ../.env
```

이후 실행 시:

```bash
source .venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --env-file ../.env
```

Backend가 정상 실행되면 다음 주소에서 확인할 수 있습니다.

- API: `http://127.0.0.1:8000`
- Health Check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

### Frontend

별도 터미널에서 실행합니다.

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 열면 Backend 연결 상태를 확인할 수 있습니다.
