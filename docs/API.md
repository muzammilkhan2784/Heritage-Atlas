# HTTP API

All application endpoints use GET. Write requests return 405. JSON is UTF-8 and responses include `X-Request-ID`.

## Search

`GET /api/sites`

| Parameter | Default | Contract |
| --- | --- | --- |
| `q` | empty | Literal case-insensitive substring of name or description; at most 120 characters |
| `language` | English | English, German, Japanese, Arabic, Hindi, French, Spanish |
| `category` | empty | Cultural, Natural, Mixed, or empty |
| `region` | empty | Exact region membership; values from `/api/metadata` |
| `lat` | absent | Finite WGS84 latitude from −90 to 90 |
| `lon` | absent | Finite WGS84 longitude from −180 to 180 |
| `radius` | absent | Kilometres, greater than zero and at most 20,000 |
| `page` | 1 | Integer 1–1,000 |
| `per_page` | 12 | Integer 1–48 |

`lat`, `lon`, and `radius` must be supplied together. Zero coordinates are valid. `NaN` and infinity are rejected. Unsupported regions simply match no records. Duplicate parameters use the first value. Geographic queries return `distance_m` in each result and sort by distance; other searches sort by name. Both have `site_id` as a stable tie-breaker.

Response shape:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "per_page": 12,
  "pages": 0
}
```

Each item includes `site_id`, `language`, `name`, `description`, `year`, `category`, `country`, `region`, nullable `area_hectares`, `location`, and `translation_note`. Optional attributed images add `image_credit` and `image_source`. Internal MongoDB `_id` and GridFS IDs are excluded. An out-of-range but syntactically valid page returns an empty list while retaining the full match total.

## Single record

`GET /api/sites/site_0001?language=Arabic` returns a single record. Missing sites or translations return 404. A language outside the supported set returns 400. `/view/site_0001?lang=Arabic` is the corresponding HTML page.

## Metadata and health

`GET /api/metadata` returns `sites` (unique IDs), `records` (all translations), `languages` (available language names), and `regions` (individual region names). The response may be cached for up to 60 seconds per worker.

`GET /health/live` returns `{"status":"ok"}` even if MongoDB is down. `/health/ready` returns `{"status":"ready"}` only if the database is reachable, records exist, and the geospatial index exists. An unseeded or unindexed database returns 503 with `status: "not_ready"` and a `reason`. A connection failure returns the generic service-unavailable error below.

## Errors

```json
{
  "error": {
    "code": "invalid_search",
    "message": "Choose a supported language.",
    "request_id": "generated-per-request"
  }
}
```

400 means invalid input, 404 means missing resource/translation, 405 means an unsupported method, and 503 means the database is unavailable or its execution budget was exceeded. The response does not expose a database URI or exception details. The browser renders corresponding readable error pages.

This API has no built-in per-client traffic limiter. Public deployments should apply limits at the ingress layer. Search responses are deliberately bounded, but totals and substring matching are not constant-cost operations.
