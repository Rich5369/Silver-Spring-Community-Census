# Silver Spring Community Census

A queryable community-intelligence map for Silver Spring, Maryland, with Fenton Village as the primary use case.

## Frontend Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

The frontend is a lightweight React + Vite application. UI components live in `src/components`, temporary display content in `src/data`, API integration helpers in `src/services`, and global presentation styles in `src/styles`.

## Run the Full Application Locally

The backend requires Python 3.12. From a second terminal:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_db
uvicorn app.main:app --reload --port 8000
```

The Census API key is not needed to serve already ingested SQLite data. A fresh checkout has an empty database; follow the ingestion instructions in [`backend/README.md`](backend/README.md) if no shared database file was provided.

Set `VITE_API_BASE_URL=/` in `.env.local`. The browser requests `/api/v1/map/community` from the frontend's own origin; Vite forwards `/api` to `http://127.0.0.1:8000`. This also works when port 5173 is forwarded from a Codespace. Restart Vite after changing environment variables. The response provides stored business points and any available Census-area polygons, including metric evidence. If the environment variable is omitted or the API request fails, the frontend falls back to clearly labeled demo data.

Open port 5173 to use the map. Port 8000 opens the backend API documentation. In a Codespace, open the forwarded port 5173 from the editor's Ports tab.

Verify the services at:

- Frontend: <http://localhost:5173>
- API health: <http://localhost:8000/health>
- API documentation: <http://localhost:8000/docs>

## Verify the Data Pipeline

```bash
npm run verify:data          # checks against http://127.0.0.1:8000
API=http://localhost:8000 npm run verify:data
```

Checks that the frontend consumes backend data correctly: that every business
record normalizes, that the insights panel's counts match the map, that no
category is unreachable through the filter chips, and that the demo fallback
stays clearly labeled.

It also exercises the Census path using the tract shape documented in
[`backend/README.md`](backend/README.md), so the day Census ingestion lands this
command reports whether the frontend will render it. The live section is skipped
when the API is not running.
