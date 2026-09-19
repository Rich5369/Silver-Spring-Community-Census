# Community Intelligence API

Backend for the Silver Spring Community Census — a queryable community-intelligence
service for **Fenton Village, Silver Spring, Maryland**, built for local businesses.

This is the scaffold only. Data ingestion is not implemented yet.

## Requirements

- Python **3.12** (the repo's Codespace also ships 3.14; this project pins 3.12)

## Setup

From the `backend/` directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional — defaults work out of the box
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>

## Test

```bash
pytest
```

## Endpoints

| Method | Path      | Description            |
| ------ | --------- | ---------------------- |
| `GET`  | `/health` | Service liveness check |

```json
{ "status": "ok", "service": "community-intelligence-api" }
```

## Configuration

All settings are environment variables with working defaults; see
[`.env.example`](.env.example). `.env` is gitignored and must never be committed.

| Variable        | Default                                              | Purpose                                     |
| --------------- | ---------------------------------------------------- | ------------------------------------------- |
| `SERVICE_NAME`  | `community-intelligence-api`                         | Identifier returned by `/health`            |
| `ENVIRONMENT`   | `development`                                        | Deployment environment label                |
| `DEBUG`         | `true`                                               | Debug flag                                  |
| `DATABASE_URL`  | `sqlite:///./data/community.db`                      | SQLAlchemy database URL                     |
| `DATABASE_ECHO` | `false`                                              | Log every SQL statement                     |
| `CENSUS_API_KEY`| _(unset)_                                            | **Secret.** US Census Data API key          |
| `CORS_ORIGINS`  | `http://localhost:5173,http://127.0.0.1:5173`        | Comma-separated allowed browser origins     |

`CORS_ORIGINS` is comma-separated rather than JSON so it stays readable in a
`.env` file or a shell export.

### Secrets

`CENSUS_API_KEY` is the only secret so far. Rules:

- The real value lives **only** in `backend/.env`, which is gitignored.
- `.env.example` keeps the key **blank**. Two tests in `tests/test_config.py`
  fail the build if a value or any long hex literal appears there.
- It is typed `SecretStr`, so it is masked in reprs, logs and tracebacks. Read
  it deliberately with `.get_secret_value()`.
- It is optional — the Census API allows 500 requests/day unkeyed, so the app
  boots and the suite passes without it.
- Request a key at <https://api.census.gov/data/key_signup.html>. Keys are
  free and per-person; if one is exposed, request a replacement and stop using
  the old one.

## Architecture

The pipeline this scaffold is shaped for:

```
public datasets → ingestion → normalization → storage → service/query → REST API → frontend
```

```
backend/
├── app/
│   ├── main.py              FastAPI app factory, CORS, lifespan
│   ├── api/
│   │   ├── router.py        aggregate router, mounted once in main.py
│   │   └── routes/          one module per resource (health.py)
│   ├── core/
│   │   ├── config.py        pydantic-settings configuration
│   │   └── database.py      SQLAlchemy engine, session, init
│   ├── models/              SQLAlchemy ORM models (base.py only so far)
│   ├── schemas/             Pydantic request/response contracts
│   ├── services/            business logic, query + evidence assembly
│   ├── repositories/        persistence access, isolating SQL from services
│   └── integrations/        outbound clients for public data sources
├── scripts/                 CLI entry points (`python -m scripts.<name>`)
├── tests/
├── data/                    SQLite runtime files (gitignored)
└── requirements.txt
```

**Layering rule:** routes translate HTTP, services hold logic, repositories touch
the database, integrations talk to the outside world. Keeping `/health` on that
path even though it is trivial means the data endpoints inherit the pattern
rather than inventing one.

### Why SQLite

Zero infrastructure, a single file that can be deleted and rebuilt by re-running
ingestion, and ample speed for one neighbourhood's public data. The
`DATABASE_URL` indirection keeps a move to Postgres a configuration change.

### Route prefixes

Routes are mounted at the application root with **no `/api` or `/v1` prefix**.
The frontend's `ENDPOINTS` table in `src/services/api.js` calls bare paths
(`/businesses`, `/community-profiles/:area`, `/sources`, `/transit`) against
`VITE_API_BASE_URL`, so matching exactly means the frontend needs no change to
talk to this service.

## Frontend integration

The frontend runs on mock data until `VITE_API_BASE_URL` is set, and falls back
to it on any request failure. To point it here:

```bash
# in the repository root, NOT in backend/
echo "VITE_API_BASE_URL=http://localhost:8000" >> .env.local
```

Confirm the connection with `curl http://localhost:8000/health` before debugging
the UI — a silent CORS failure looks identical to demo-data mode.

## Evidence and provenance

Every data-derived response must carry the evidence behind it: **dataset, year,
geography, metric/variable where applicable, and source URL or identifier.**

No fact-bearing tables exist yet. When they do, each will carry a foreign key to
a `sources` row, so a value cannot be stored — or served — without its citation.

## Not implemented yet

- Census ACS ingestion
- OpenStreetMap / Overpass ingestion
- Domain models, repositories and services beyond the health scaffold
- `/businesses`, `/community-profiles/:area`, `/sources`, `/transit`
