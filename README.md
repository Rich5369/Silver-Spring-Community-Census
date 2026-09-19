# Silver Spring Community Census

A queryable community-intelligence map for Silver Spring, Maryland, with Fenton Village as the primary use case.

## Frontend Setup

```bash
npm install
npm run dev
```

The frontend is a lightweight React + Vite application. UI components live in `src/components`, temporary display content in `src/data`, API integration helpers in `src/services`, and global presentation styles in `src/styles`.

## Backend Integration Contract

Set `VITE_API_BASE_URL` to the backend origin, without a trailing slash. If it is omitted, or if a configured API request fails, the frontend safely displays its clearly labeled demo data.

The frontend uses the backend's versioned API contract:

- `GET /api/v1/map/community`
- `GET /api/v1/insights/fenton-village`

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
