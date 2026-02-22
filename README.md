# AI Legal Assistant

AI Legal Assistant is a modular Django + React project for document-level legal analysis with explainable findings.

## Current Capabilities (Phase 2 Complete)

The project currently supports:
- Uploading legal documents (`.txt`, `.pdf`, `.csv`, `.xlsx`)
- Clause extraction
- Deterministic rule checks plus LLM analysis
- Always-async review execution (`POST /v1/review/run` returns `run_id`)
- Review run lifecycle tracking (`queued`, `running`, `succeeded`, `failed`, `partial`)
- Idempotency keys, concurrency caps, and request rate limits for review execution
- Persisted chunk artifacts with stable `chunk_id` provenance
- Run-level instrumentation (`token_usage`, `stage_timings`, cache hit/miss fields)
- Persisting review runs and findings
- Retrieving findings by document (optionally by run)
- A minimal React + TypeScript UI for upload, run, and findings review

## Tech Stack

- Backend: Django 5 + Django REST Framework
- LLM: OpenAI API with strict JSON schema validation
- Auth library available: `djangorestframework-simplejwt`
- Database:
  - SQLite for local dev by default
  - PostgreSQL 16 in Docker Compose
- Frontend: React 18 + TypeScript + Vite
- Container orchestration: Docker Compose
- Async jobs: Celery + Redis

## Repository Layout

```text
ai-legal-assistant/
|-- apps/
|   |-- accounts/
|   |-- documents/
|   `-- review/
|-- backend/
|-- docker/
|-- docs/
|-- frontend/
|-- docker-compose.yml
|-- Dockerfile
|-- manage.py
`-- requirements.txt
```

## API Endpoints (Implemented)

- `GET /` - health check
- `POST /v1/documents/upload` - upload/ingest a document
- `POST /v1/review/run` - enqueue clause extraction + rules + LLM analysis (returns `run_id`)
- `GET /v1/review-runs/{id}` - retrieve run status/progress for a review run
- `GET /v1/documents/{id}/findings` - retrieve findings for latest run
- `GET /v1/documents/{id}/findings?run_id=<uuid>` - retrieve findings for a specific run

## Async Run Semantics

- `POST /v1/review/run` response codes:
  - `202 Accepted`: run was queued and task enqueue succeeded
  - `200 OK`: idempotency key reused an existing unexpired run
  - `409 Conflict`: idempotency key exists but is expired (older than 24h)
  - `429 Too Many Requests`: concurrency or rate limit reached
  - `503 Service Unavailable`: enqueue failed
- Run status values:
  - `queued`, `running`, `succeeded`, `failed`, `partial`
- Partial-result policy:
  - If deterministic stages succeed but LLM stage fails/timeouts, run is marked `partial`.
  - Rule findings are still persisted and retrievable for that run.

## Run Locally (Backend + Frontend)

1. Create and activate a virtual environment.
2. Install backend dependencies.
3. Apply migrations.
4. Run the backend.
5. Install frontend dependencies and run Vite.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Required for async review execution in a third terminal:

```powershell
celery -A backend worker -l info
```

URLs:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Run with Docker Compose

```powershell
docker compose up --build
```

Compose services:
- `db` (PostgreSQL 16)
- `redis` (Celery broker/result backend)
- `web` (Django API on port 8000)
- `worker` (Celery worker)
- `frontend` (Vite dev server on port 5173)

## Environment

Use `.env` (or copy from `.env.example`) for configuration:
- `LLM_PROVIDER` (`mock` or `openai`)
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `REVIEW_MAX_CONCURRENT_RUNS`, `REVIEW_RATE_LIMIT_PER_MINUTE`
- `REVIEW_ENABLE_PIPELINE_CACHE`, `REVIEW_CACHE_TTL_SECONDS`

Note:
- If `LLM_PROVIDER=mock`, analysis runs without external API calls.
- If `LLM_PROVIDER=openai` and no API key is set, the code falls back to mock findings.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test -v 1
cd frontend; npm run build
```

## Project Docs

- `docs/MVP_Checklist.md`
- `docs/PHASE_2_Checklist.md`
- `docs/POST_MVP_PLAN.md`
- `docs/AI_Legal_ARCHITECTURE.md`
- `docs/verification_logs/`

## License

MIT
