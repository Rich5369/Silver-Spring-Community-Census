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

## API

Base URL in development: `http://localhost:8000`. All data endpoints are
prefixed **`/api/v1`**.

Interactive docs: <http://localhost:8000/docs> · Schema:
<http://localhost:8000/openapi.json>

| Method | Path                              | Description                          |
| ------ | --------------------------------- | ------------------------------------ |
| `GET`  | `/health`                         | Liveness check (unversioned)         |
| `GET`  | `/api/v1/areas`                   | List geographic areas                |
| `GET`  | `/api/v1/areas/{geoid}`           | One area by GEOID                    |
| `GET`  | `/api/v1/areas/{geoid}/metrics`   | Metrics for an area, with evidence   |
| `GET`  | `/api/v1/businesses`              | Businesses, filterable by category   |
| `GET`  | `/api/v1/businesses/categories`   | Categories present, with counts      |
| `GET`  | `/api/v1/map/community`           | Both map layers as GeoJSON           |

### Conventions

- **Join on `geoid`, never on `name`.** Tract names are neither unique nor
  stable across ACS vintages.
- **`null` means "not available", never zero.** The Census suppresses
  estimates for small populations; a suppressed metric has `"value": null`
  and still carries full evidence.
- **Every metric includes `evidence`.** There is no response shape that
  returns a number without its dataset, year, variable and source URL.
- **An empty result is a 200, not a 404.** Filtering to a category with no
  matches returns `{"businesses": []}`. Only an unknown GEOID is a 404.
- **GeoJSON positions are `[longitude, latitude]`** per RFC 7946 — the
  reverse of Leaflet's `[lat, lng]`. `L.geoJSON` converts for you;
  hand-built markers do not.

### Examples

All payloads below are real responses, trimmed for length.

#### `GET /api/v1/areas?with_boundary_only=true`

`with_boundary_only=true` returns the 14 Silver Spring study-area tracts that
have map geometry. Without it you get every ingested area (233).

```json
{
  "count": 1,
  "areas": [
    {
      "geoid": "24031701701",
      "name": "Census Tract 7017.01; Montgomery County; Maryland",
      "geography_type": "tract",
      "state_fips": "24",
      "county_fips": "031",
      "tract_code": "701701",
      "has_boundary": true
    }
  ]
}
```

Optional query parameters: `geography_type` (`tract`, `county`, …),
`with_boundary_only` (bool), `limit` (1–1000).

#### `GET /api/v1/areas/24031701701/metrics`

22 metrics per tract. Derived metrics record the full formula in
`source_variable`, so any number can be reproduced from the published tables.

```json
{
  "area": { "geoid": "24031701701", "name": "Census Tract 7017.01; Montgomery County; Maryland", "...": "..." },
  "count": 22,
  "metrics": [
    {
      "metric_key": "bachelors_or_higher_share",
      "value": 66.93,
      "unit": "percent",
      "evidence": {
        "dataset": "American Community Survey 5-Year Estimates (2024)",
        "dataset_year": 2024,
        "source_variable": "(B15003_022E + B15003_023E + B15003_024E + B15003_025E) / B15003_001E * 100",
        "source_url": "https://api.census.gov/data/2024/acs/acs5",
        "organization": "US Census Bureau"
      }
    }
  ]
}
```

Available `metric_key` values: `total_population`, `median_household_income`,
`median_age`, `young_adults_20_34`, `young_adult_share`,
`occupied_housing_units`, `owner_occupied_households`,
`renter_occupied_households`, `renter_share`, `commuters_total`,
`commute_drove_alone`, `commute_carpooled`, `commute_public_transport`,
`commute_walked`, `commute_bicycle`, `worked_from_home`,
`commute_active_share`, `worked_from_home_share`, `bachelors_or_higher`,
`bachelors_or_higher_share`, `multilingual_households`,
`multilingual_household_share`.

#### `GET /api/v1/businesses/categories`

Built from stored rows, so every category listed has at least one business
behind it. Use it to build filter controls that cannot return empty.

```json
{
  "count": 10,
  "categories": [
    { "category": "Restaurant", "count": 77 },
    { "category": "Retail", "count": 35 },
    { "category": "Professional Services", "count": 34 },
    { "category": "Personal Care", "count": 20 },
    { "category": "Cafe", "count": 15 },
    { "category": "Grocery", "count": 13 },
    { "category": "Health Services", "count": 9 }
  ]
}
```

#### `GET /api/v1/businesses?category=Cafe&limit=1`

```json
{
  "businesses": [
    {
      "id": 174,
      "name": "'TIS Corner Cafe",
      "category": "Cafe",
      "latitude": 38.9925641,
      "longitude": -77.0309487,
      "address": "1317 East-West Highway, 20910",
      "source": "OpenStreetMap contributors (node/14118971901)",
      "source_url": "https://www.openstreetmap.org/copyright",
      "external_id": "node/14118971901",
      "source_tag": "amenity=cafe",
      "dataset": "OpenStreetMap POIs via Overpass API"
    }
  ]
}
```

Query parameters: `category` (exact, case-sensitive), `q` (case-insensitive
name search), `limit` (1–1000). `address` may be `null` — about 20% of OSM
records carry no address tags.

#### `GET /api/v1/map/community`

Two standard FeatureCollections, each usable directly with `L.geoJSON`. They
are separate because the layers are drawn differently — choropleth polygons
vs point markers — and mixing them would force the client to partition again.

```json
{
  "areas": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": "24031701701",
        "geometry": { "type": "Polygon", "coordinates": [[[-77.03, 38.99], "..."]] },
        "properties": {
          "geoid": "24031701701",
          "name": "Census Tract 7017.01; Montgomery County; Maryland",
          "geography_type": "tract",
          "boundary_source": {
            "dataset": "TIGERweb Census Tracts (ACS 2024 vintage)",
            "dataset_year": 2024,
            "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2024/MapServer/8",
            "organization": "US Census Bureau"
          },
          "metrics": {
            "total_population": {
              "value": 3503.0,
              "unit": "people",
              "evidence": { "dataset": "American Community Survey 5-Year Estimates (2024)", "source_variable": "B01003_001E", "...": "..." }
            }
          }
        }
      }
    ]
  },
  "businesses": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": "node/13021040594",
        "geometry": { "type": "Point", "coordinates": [-77.0242101, 38.9953504] },
        "properties": {
          "geoid": "node/13021040594",
          "name": "&pizza",
          "geography_type": "business",
          "metrics": {},
          "business": {
            "id": 155,
            "category": "Restaurant",
            "address": "8455 Fenton Street, Silver Spring, MD 20910",
            "source": "OpenStreetMap contributors (node/13021040594)",
            "source_url": "https://www.openstreetmap.org/copyright",
            "source_tag": "amenity=fast_food"
          }
        }
      }
    ]
  },
  "area_count": 14,
  "business_count": 207
}
```

Note `boundary_source` is cited separately from each metric's `evidence`:
boundaries and estimates are different products with different vintages.

#### Errors

Unknown GEOID:

```
GET /api/v1/areas/24031999999   →   404
{ "detail": "No area found with GEOID '24031999999'." }
```

Invalid parameter (`limit=0`) returns FastAPI's standard `422` validation
body. An unknown `category` is **not** an error — it returns `200` with an
empty list.

#### `GET /health`

```json
{ "status": "ok", "service": "community-intelligence-api" }
```

### Unversioned legacy routes

`/businesses` and `/geographies` are still served, unprefixed, because the
frontend's `ENDPOINTS` table in `src/services/api.js` calls bare paths. They
are hidden from the OpenAPI schema so the documented contract is the `/api/v1`
one, and can be removed once the frontend migrates.

## Configuration

All settings are environment variables with working defaults; see
[`.env.example`](.env.example). `.env` is gitignored and must never be committed.

| Variable        | Default                                              | Purpose                                     |
| --------------- | ---------------------------------------------------- | ------------------------------------------- |
| `SERVICE_NAME`  | `community-intelligence-api`                         | Identifier returned by `/health`            |
| `ENVIRONMENT`   | `development`                                        | Deployment environment label                |
| `SSCC_DEBUG`    | `true`                                               | Backend debug flag                          |
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
- It is optional for serving existing SQLite data and for running the suite.
  The upstream Census API may require it for a fresh ingestion.
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
