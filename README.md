# Medical Data Extractor

Upload a medical PDF (e.g. a CPAP / DME order fax) and get back a structured order:
patient, provider, items, diagnoses, signatures. The app keeps a persistent record of
every extraction so it can be browsed, edited, and audited later.

- **Backend**: FastAPI + SQLAlchemy + Postgres, OpenAI for PDF → JSON extraction.
- **Frontend**: React 18 + Vite + TypeScript + MUI 6.
- **Deploy**: Cloud Run (frontend + backend), Cloud SQL Postgres, Secret Manager.

Live (staging): <https://mde-frontend-970398036042.us-central1.run.app>

---

## Repository layout

```
medical-data-extractor/
├── backend/                       FastAPI service
│   ├── app/
│   │   ├── main.py                App factory, middleware wiring
│   │   ├── api/v1/
│   │   │   ├── router.py          Mounts feature routers under /api/v1
│   │   │   ├── routes/            HTTP route definitions
│   │   │   └── controllers/       Per-resource business logic
│   │   ├── core/                  Config, logging, security (API-key auth)
│   │   ├── db/                    Engine + Session
│   │   ├── middleware/            request_id, error envelope, rate-limit, CORS, audit
│   │   ├── models/                SQLAlchemy ORM (Order, Patient, ActivityLog)
│   │   ├── repositories/          DB access layer
│   │   ├── schemas/               Pydantic request/response models
│   │   └── services/              PDF text extraction, OpenAI extraction, caching
│   ├── tests/                     pytest suite
│   └── alembic.ini                migrations config
├── frontend/                      React SPA (Vite)
│   ├── src/
│   │   ├── App.tsx                tab shell (Upload / Orders / Patients / Activity)
│   │   ├── components/            UploadPanel, OrdersPanel, PatientsPanel, ...
│   │   ├── lib/api.ts             typed client wrapper
│   │   └── types/api.ts           shared response types
│   ├── nginx.conf                 prod reverse-proxy template (envsubst at boot)
│   └── Dockerfile                 multi-stage: vite build → nginx
├── Dockerfile                     backend image (used by Cloud Run)
├── docker-compose.yml             local Postgres (and optional Adminer)
├── requirements.txt               backend Python deps
└── README.md
```

---

## API endpoints

All endpoints live under `/api/v1` and require an `X-API-Key` header (when
`REQUIRE_AUTH=true`). All responses are JSON.

### Health

| Method | Path                | Description                 |
| ------ | ------------------- | --------------------------- |
| GET    | `/api/v1/health`    | Liveness check              |
| GET    | `/api/v1/health/db` | Database connectivity check |

### Extraction

| Method | Path                  | Description                                                                                 |
| ------ | --------------------- | ------------------------------------------------------------------------------------------- |
| POST   | `/api/v1/extractions` | Upload a PDF (`multipart/form-data`), returns the structured extraction and persisted order |

### Orders

| Method | Path                        | Description                             |
| ------ | --------------------------- | --------------------------------------- |
| GET    | `/api/v1/orders`            | List orders (`?search=&status=&limit=`) |
| POST   | `/api/v1/orders`            | Create an order manually                |
| GET    | `/api/v1/orders/{order_id}` | Get one order                           |
| PATCH  | `/api/v1/orders/{order_id}` | Update an order                         |
| DELETE | `/api/v1/orders/{order_id}` | Delete an order                         |

### Patients

| Method | Path                                   | Description               |
| ------ | -------------------------------------- | ------------------------- |
| GET    | `/api/v1/patients`                     | List unique patients      |
| GET    | `/api/v1/patients/{patient_id}`        | Get patient detail        |
| GET    | `/api/v1/patients/{patient_id}/orders` | List orders for a patient |

### Activity logs

| Method | Path                    | Description                                   |
| ------ | ----------------------- | --------------------------------------------- |
| GET    | `/api/v1/activity-logs` | Audit trail (CRUD + extraction + auth events) |

Interactive docs (Swagger UI) are served at `/docs` and OpenAPI JSON at
`/openapi.json` when `DEBUG=true`.

---

## Error envelope

Every error response uses a single, predictable shape so clients can render and log
uniformly:

```json
{
  "error": {
    "type": "validation_error",
    "message": "Request validation failed",
    "status_code": 422,
    "details": [],
    "request_id": "01HXYZ..."
  }
}
```

`details` is optional (present for validation errors). `request_id` is the
correlation id, also returned as the `X-Request-ID` response header.

`type` values you can expect:

| `type`             | When                                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| `http_error`       | Any `HTTPException` raised by a handler (404, 401, …)                                                      |
| `validation_error` | Pydantic / FastAPI request-validation failure (422)                                                        |
| `internal_error`   | Unhandled exception (500). Message is generic; details are in server logs under the matching `request_id`. |

---

## Local development

Requirements: Python ≥ 3.11, Node ≥ 20, Docker.

### 1. Start Postgres

```bash
docker compose up -d postgres
# Postgres is exposed on localhost:5434
# DB:  medical_data    user/pass: hde / hde
```

Optionally start the Adminer UI at <http://localhost:8081>:

```bash
docker compose --profile ui up -d adminer
```

### 2. Start the backend

```bash
cd backend
cp .env.example .env             # edit values (see below)
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
pip install "uvicorn[standard]" pdfplumber pytest   # local-dev extras

# Apply DB schema (Alembic)
alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

API is now at <http://localhost:8000/api/v1>, docs at <http://localhost:8000/docs>.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Vite proxies `/api/*` to `http://localhost:8000` (see `vite.config.ts`), so the SPA
calls the backend with same-origin relative URLs.

### Run the tests

```bash
cd backend
pytest
```

---

## Environment configuration

All backend config lives in `backend/.env` (loaded by `app/core/config.py`).
The frontend reads `VITE_*` vars from `frontend/.env.local` at build time.

### Backend (`backend/.env`)

| Variable                    | Default / example                                          | Notes                                                          |
| --------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------- |
| `ENVIRONMENT`               | `development`                                              | `development` \| `production`                                  |
| `DEBUG`                     | `true`                                                     | Enables `/docs` and verbose logs                               |
| `DATABASE_URL`              | `postgresql+psycopg://hde:hde@localhost:5434/medical_data` | SQLAlchemy URL. In prod use the Cloud SQL socket form.         |
| `REQUIRE_AUTH`              | `true`                                                     | When true, all `/api/v1/*` (except `/health`) need `X-API-Key` |
| `API_KEY`                   | _random 32-byte hex_                                       | The accepted API key. Generate with `openssl rand -hex 32`.    |
| `CORS_ORIGINS`              | `http://localhost:5173,http://127.0.0.1:5173`              | Comma-separated, or `*`                                        |
| `RATE_LIMIT_DEFAULT`        | `30/minute`                                                | slowapi syntax                                                 |
| `RATE_LIMIT_UPLOAD`         | `5/minute`                                                 | Applied to `/extractions`                                      |
| `MAX_UPLOAD_SIZE_MB`        | `10`                                                       |                                                                |
| `ALLOWED_UPLOAD_MIME_TYPES` | `application/pdf`                                          | Comma-separated                                                |
| `OPENAI_API_KEY`            | `sk-...`                                                   | Required for real extraction                                   |
| `OPENAI_MODEL`              | `gpt-5.4`                                                  | Use `gpt-5.4-mini` for cheaper runs                            |
| `OPENAI_REASONING_EFFORT`   | `low`                                                      | `low` \| `medium` \| `high` (reasoning models only)            |
| `LLM_TIMEOUT_SECONDS`       | `45`                                                       |                                                                |
| `LLM_MAX_RETRIES`           | `2`                                                        |                                                                |

### Frontend (`frontend/.env.local`)

| Variable            | Example                           | Notes                                          |
| ------------------- | --------------------------------- | ---------------------------------------------- |
| `VITE_API_BASE_URL` | _empty_ (use the dev proxy)       | Set to a full URL only for non-proxied builds. |
| `VITE_API_KEY`      | _same value as backend `API_KEY`_ | Sent as `X-API-Key` from the SPA in dev.       |

In production these are **not** used — the nginx sidecar injects `X-API-Key` from
Secret Manager so the key never reaches the browser.

---

## Deploy to GCP

Target architecture:

- **Backend** → Cloud Run service `mde-backend` (containerised FastAPI on `:8080`)
- **Frontend** → Cloud Run service `mde-frontend` (nginx serving the Vite build, proxying `/api/*` to the backend with `X-API-Key` injected from Secret Manager)
- **Database** → Cloud SQL for Postgres instance `hde-pg`, database `medical_data`
- **Secrets** → Secret Manager (`API_KEY`, `OPENAI_API_KEY`, `DB_PASSWORD`)

Set common variables once:

```bash
export PROJECT_ID=monsteria-core-staging
export REGION=us-central1
export SQL_INSTANCE=hde-pg
gcloud config set project "$PROJECT_ID"
```

### 1. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Provision Cloud SQL

```bash
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_16 \
  --region="$REGION" \
  --tier=db-f1-micro \
  --storage-size=10GB

gcloud sql databases create medical_data --instance="$SQL_INSTANCE"
gcloud sql users create hde --instance="$SQL_INSTANCE" --password='<choose-one>'
```

Apply the schema (one-off, from your laptop using the Cloud SQL Auth Proxy):

```bash
cloud-sql-proxy "$PROJECT_ID:$REGION:$SQL_INSTANCE" &
DATABASE_URL='postgresql+psycopg://hde:<pass>@localhost:5432/medical_data' \
  alembic -c backend/alembic.ini upgrade head
```

### 3. Create secrets

```bash
printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create API_KEY --data-file=-
printf '%s' "sk-..."                  | gcloud secrets create OPENAI_API_KEY --data-file=-
printf '%s' "<db-password>"           | gcloud secrets create DB_PASSWORD --data-file=-
```

### 4. Deploy the backend

```bash
gcloud run deploy mde-backend \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --add-cloudsql-instances "$PROJECT_ID:$REGION:$SQL_INSTANCE" \
  --set-env-vars "ENVIRONMENT=production,DEBUG=false,REQUIRE_AUTH=true,CORS_ORIGINS=*,OPENAI_MODEL=gpt-5.4,OPENAI_REASONING_EFFORT=low" \
  --set-env-vars "DATABASE_URL=postgresql+psycopg://hde:PASSWORD_PLACEHOLDER@/medical_data?host=/cloudsql/$PROJECT_ID:$REGION:$SQL_INSTANCE" \
  --set-secrets "API_KEY=API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest"
```

> The `DATABASE_URL` uses the Unix-socket form Cloud Run mounts at
> `/cloudsql/<connection-name>`. If you prefer to interpolate the password from
> Secret Manager, mount it as `DB_PASSWORD` and build the URL in code instead.

Note the printed URL — call it `BACKEND_URL`.

### 5. Deploy the frontend

The frontend is just nginx serving `dist/` and reverse-proxying `/api/*` to the
backend. Three env vars drive `nginx.conf`:

```bash
BACKEND_URL=$(gcloud run services describe mde-backend --region "$REGION" \
              --format='value(status.url)')
BACKEND_HOST=${BACKEND_URL#https://}

cd frontend
gcloud run deploy mde-frontend \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "BACKEND_URL=$BACKEND_URL,BACKEND_HOST=$BACKEND_HOST" \
  --set-secrets "API_KEY=API_KEY:latest"
```

Open the printed Service URL — that's the app.

### 6. Subsequent deploys

Both services support source deploys, so iterating is just:

```bash
# backend
gcloud run deploy mde-backend  --source . --region "$REGION"

# frontend
cd frontend && gcloud run deploy mde-frontend --source . --region "$REGION"
```

Existing env vars and secret bindings are preserved when you don't pass
`--set-env-vars` / `--set-secrets`.

## How extraction works

`POST /api/v1/extractions` is the heart of the app. The pipeline is intentionally
small and synchronous so the user gets feedback within a single request:

1. **Validate the upload.** The route enforces `Content-Type` (PDF only),
   `MAX_UPLOAD_SIZE_MB`, non-empty body, and a `%PDF` magic-bytes check. Each
   layer rejects with the appropriate HTTP status (`415`, `413`, `400`).
2. **Content-hash dedupe.** The PDF bytes are SHA-256'd and looked up in an
   in-memory cache (`services/extraction_cache.py`). A repeat upload of the same
   file short-circuits the LLM call entirely and returns the previous result.
3. **Pull the raw text.** `services/pdf_text.py` runs `pdfplumber` over the file
   to get a best-effort plain-text rendition. This is used both as fallback
   input and to enable cheap heuristic extraction when the LLM is unavailable.
4. **Call the LLM (preferred path).** When `OPENAI_API_KEY` is set the PDF is
   sent to OpenAI as a base64-encoded image attachment alongside a strict JSON
   schema prompt (see `_RICH_JSON_SCHEMA_HINT` in `services/extraction.py`). The
   model returns JSON-only output that we parse and coerce into typed Pydantic
   schemas (`PatientExtraction`, `DocumentDetails`, `OrderedItem`, …). Timeouts
   and retries are governed by `LLM_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES`.
5. **Heuristic fallback.** If the LLM is not configured, fails repeatedly, or
   returns malformed JSON, the service falls back to regex / keyword extraction
   over the raw text so the endpoint still returns _something_ structured.
6. **Persist.** The extraction is upserted into a `Patient` row (matched on
   first/last name + DOB) and a new `Order` row with `status=completed` plus the
   full `document_metadata` JSON. The original filename is preserved for audit.
7. **Audit + respond.** The middleware writes an `ActivityLog` entry with the
   request id and returns the typed `ExtractionResponse` (extraction payload +
   the persisted order).

The frontend renders the response via `DocumentDetailsView` and offers a
"Raw order JSON" copy-to-clipboard for debugging.

---

## What's next

A few concrete improvements queued up for when this graduates from a prototype:

- **Production database migrations.** Today the schema is applied with a
  one-shot `alembic upgrade head` from a developer laptop using the Cloud SQL
  Auth Proxy. The next step is to make migrations a first-class deploy step:
  bake `alembic upgrade head` into a Cloud Run Job (or a pre-deploy Cloud Build
  step) that runs against the target database before the new backend revision
  receives traffic, with automatic rollback if the migration fails. Migrations
  themselves should follow expand-and-contract (additive change → backfill →
  drop) so the old and new app versions can coexist during the rollout.

- **Lossless PDF → text → LLM extraction.** Currently the PDF is sent to the
  LLM as an image, which gives good results on scanned faxes but burns tokens,
  is slow, and is hard to evaluate offline. A better pipeline is to first
  perform a lossless conversion of the PDF (text layer + per-page OCR for
  scanned pages, with bounding boxes preserved) and feed that structured text
  to the model. That gives us deterministic input to test against, much lower
  per-call cost, the ability to swap models freely, and richer error
  attribution (we know which page / region a field came from).

- **Proper authentication.** The current `X-API-Key` is a single shared secret
  injected by nginx — fine for a demo, not for real users. The plan is an
  OAuth2 / OIDC login (Google + email/password via something like Auth0,
  Clerk, or a self-hosted Keycloak), per-user sessions, role-based access on
  orders/patients, and signed audit entries that attribute every action to a
  real principal instead of "the API key".

- **CI/CD instead of `gcloud run deploy --source .`** Deploying from a laptop
  is fast but doesn't scale and provides no safety net. The next iteration is
  a GitHub Actions pipeline that on every push to `main`: runs the backend
  pytest suite + frontend type-check, builds both images via Cloud Build,
  pushes them to Artifact Registry, runs Alembic migrations as a Cloud Run
  Job, deploys the backend with `--no-traffic`, smoke-tests the new revision,
  then shifts traffic 0 → 10 → 100% with automatic rollback on error-rate
  regression. PR builds would deploy to a preview environment.
