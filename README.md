# Silver Spring Community Census

A queryable community-intelligence map for Silver Spring, Maryland, with Fenton Village as the primary use case.

## Frontend Setup

```bash
npm install
npm run dev
```

The frontend is a lightweight React + Vite application. UI components live in `src/components`, temporary display content in `src/data`, API integration helpers in `src/services`, and global presentation styles in `src/styles`.

### Hosted deployment

The current demo is hosted on Render:

- Frontend: https://silver-spring-community-census-1.onrender.com
- Backend API: https://silver-spring-community-census.onrender.com

The frontend is a Render Static Site. Its build command is `npm run build`,
its publish directory is `dist`, and its environment variable is:

```text
VITE_API_BASE_URL=https://silver-spring-community-census.onrender.com
```

The backend is a Render Web Service built from `backend/`. Its production
environment must include:

```text
ENVIRONMENT=production
SSCC_DEBUG=false
CORS_ORIGINS=https://silver-spring-community-census-1.onrender.com
```

After changing frontend environment variables, choose **Save and rebuild** in
Render. A save-only operation does not rebuild the static bundle.

Verify the hosted deployment:

```bash
curl https://silver-spring-community-census.onrender.com/health
curl 'https://silver-spring-community-census.onrender.com/api/v1/map/community'
curl 'https://silver-spring-community-census.onrender.com/api/v1/areas?with_boundary_only=true'
```

The populated demo should report 14 areas and 207 businesses. The frontend
should show the map, tract boundaries, business markers, ACS metrics, and the
evidence-backed question panel.

#### Restore a lost or recreated host

If the Render service or site is lost, recreate them from the same GitHub
repository and branch (`main`). For the frontend, use the repository root,
`npm run build`, and `dist`. For the backend, use root directory `backend/`
and the Docker runtime. Set the environment variables above before deploying.

The backend image contains `backend/data/community.seed.db`; the startup
configuration copies that baked snapshot into the runtime database when needed.
Do not rely on an uncommitted local SQLite file or on a free-tier ephemeral
filesystem. After recreation, check that the API returns `area_count: 14` and
`business_count: 207` before sharing the frontend URL.

### Vercel deployment (optional)

Import the repository into Vercel with the project root set to the repository
root. `vercel.json` supplies the Vite build and SPA fallback. Add this Vercel
environment variable for the deployed backend:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-HOST
```

The backend must add the exact Vercel deployment origin to its
`CORS_ORIGINS`, for example:

```text
CORS_ORIGINS=https://silver-spring-community-census.vercel.app
```

After deployment, verify `/api/v1/map/community`, `/api/v1/areas?with_boundary_only=true`,
and `POST /api/v1/query` from the browser. The frontend no longer treats a
missing API response as live data.

## Backend Integration Contract

Set `VITE_API_BASE_URL` to the backend origin, without a trailing slash. When it is omitted, the frontend uses the same-origin `/api` contract (and the Vite development proxy locally). If the API cannot be reached, the UI reports the connection failure instead of presenting the result as live data.

The frontend uses the backend's versioned API contract:

- `GET /api/v1/map/community`
- `GET /api/v1/insights/fenton-village`
- `GET /api/v1/government/summary`

To build historical ACS coverage for government trend views, ingest supported
5-year vintages separately. Each run keeps its year as part of the evidence
source and is safe to repeat:

```bash
cd backend
python scripts/ingest_census.py --year 2023
python scripts/ingest_census.py --year 2022
python scripts/ingest_geographies.py
```

The current seeded demo contains the 2024 vintage. Historical trend charts
must remain unavailable until older vintages have been ingested; the UI must
not infer a trend from one year.

### Government planning summary

The civic planning endpoint returns the evidence-backed study-area snapshot,
including population, housing tenure, age and income ranges, community
composition, mapped business mix, tract coverage, and source evidence. It also
lists views that are intentionally unavailable until historical data is
ingested, such as year-over-year trends and displacement. The API does not
infer causation or produce a policy score.

### Businesses Response

Businesses are read from the `businesses.features` GeoJSON layer in the map response; the headline profile is adapted from the evidence-backed insights response.

Return this exact envelope. `businesses` may be an empty array. Coordinates must be JSON numbers; records without a name or valid coordinates are discarded by the adapter.

```json
{
  "businesses": [
    {
      "id": 1,
      "name": "Example Business",
      "category": "Restaurant",
      "latitude": 38.9921,
      "longitude": -77.0242,
      "address": "123 Example Street, Silver Spring, MD",
      "source": "Organization or dataset name",
      "sourceIds": ["business-directory-2026"]
    }
  ]
}
```

### Community Profile Response

Return this exact envelope. Unknown numeric statistics should be `null`, not formatted strings. The frontend handles formatting and missing values.

```json
{
  "profile": {
    "areaName": "Fenton Village",
    "summary": "Short, plain-language description of the selected area.",
    "dataStatus": "Provisional data",
    "statistics": {
      "population": 8200,
      "medianHouseholdIncome": 84000,
      "language": {
        "label": "Multilingual households",
        "value": 38,
        "unit": "percent"
      },
      "businessCount": 14,
      "restaurantCount": 2,
      "retailCount": 2
    },
    "statisticSources": {
      "population": ["acs-dp05-2024"],
      "income": ["acs-s1901-2024"],
      "language": ["acs-s1601-2024"],
      "businesses": ["business-directory-2026"],
      "restaurants": ["business-directory-2026"],
      "retail": ["business-directory-2026"]
    }
  }
}
```

Sources are requested separately and use this envelope:

```json
{
  "sources": [
    {
      "id": "acs-s1901-2024",
      "organization": "",
      "dataset": "",
      "year": "",
      "geography": "",
      "table": "",
      "url": ""
    }
  ]
}
```

### Community-area GeoJSON

No boundary dataset is bundled with the frontend. When real geographic data is available, pass a standard GeoJSON `FeatureCollection` to the map's `communityGeoJson` input. Feature properties may contain available values and source metadata; `null` values display as `Data unavailable` rather than zero or an estimate.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "stable-area-id",
      "properties": {
        "areaName": "",
        "population": null,
        "medianIncome": null,
        "source": null
      },
      "geometry": null
    }
  ]
}
```

`source` may be `null`, one source object, or an array of source objects using the source fields documented above. Real features must include valid GeoJSON geometry before the layer is enabled.

## Verify the Data Pipeline

```bash
npm run verify:data          # checks against http://127.0.0.1:8000
API=http://localhost:8000 npm run verify:data
```

Checks that the frontend consumes backend data correctly: that every business
record normalizes, that the insights panel's counts match the map, that no
category is unreachable through the filter chips, and that the demo fallback
stays clearly labeled. The live section is skipped when the API is not running.
