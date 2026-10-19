# UNESCO World Heritage Explorer

### Heritage Atlas — extraordinary places, enduring stories.

[![Quality checks](https://github.com/muzammilkhan2784/UNESCO-World-Heritage-Explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/muzammilkhan2784/UNESCO-World-Heritage-Explorer/actions/workflows/ci.yml)

A multilingual heritage atlas built with **Flask, MongoDB, PyMongo, GridFS, and Leaflet**. Search a historical collection of **1,155 sites and 5,639 language records**, explore nearby places using spherical distance, and keep private field notes. Includes a validated dataset, native MongoDB setup, REST endpoints, and tests against real MongoDB.

![Heritage Atlas desktop interface](docs/images/explorer.png)

## Try it locally

Requires Python 3.10+ on Windows x64. **Double-click `Start-Demo.cmd`**, or run:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/bootstrap.py
python scripts/install_mongodb.py
python scripts/run_local.py
```

Open **[localhost:5050](http://localhost:5050)**. The launcher starts native MongoDB with authentication, builds indexes, imports the bundled snapshot, and serves Flask through Waitress. Press Ctrl+C in its terminal to stop. The database persists in `.runtime/data/`. No API keys or containers are required.

The project-local MongoDB installer supports Windows x64 and Ubuntu 24.04 x64, downloads Community 8.0.34 from the official MongoDB distribution, and verifies its SHA-256 checksum. It does not create a system service or change your original coursework database. Other platforms can install MongoDB independently and put `mongod` on PATH. Alternatively, set `MONGO_URI` and `MONGO_DB` to use an existing MongoDB or Atlas database; the launcher then leaves that server under your control.

Keep `.env` private. Generating a new `.env` does not rotate passwords inside an existing database. Repeating the import updates records by `(site_id, language)` without deleting existing data. See [operations](docs/OPERATIONS.md).

## What it does

- **Discover:** literal, case-insensitive keyword search across names and descriptions, combined with category and region filters.
- **Find nearby:** MongoDB `$geoNear` and a `2dsphere` index return distances in metres and sort the full matching set before pagination. Input uses latitude/longitude; GeoJSON stores **longitude first**.
- **Explore visually:** map markers match the current results page, link to site details, and let visitors select a search origin. Search and detail pages remain usable when map tiles are unavailable.
- **Read across languages:** English, Arabic, French, German, Hindi, Japanese, and Spanish. Each detail page lists only the translations available for that site, with language and direction attributes for multilingual text.
- **Keep field notes:** save and delete notes in browser local storage, shared across translations of the same site. No account, public posting, or server-side storage of notes.
- **Serve media:** an operator CLI links attributed raster images through GridFS. Media responses include cache validators; missing or unsupported images use a bundled illustration.
- **Operate predictably:** environment-based database credentials, security headers, bounded database queries, request IDs, liveness/readiness endpoints, and automated checks.

## Data, honestly

This is the **original ISTE 438 coursework snapshot, with inscription years through 2021**, recovered from the local MongoDB export. It is not a current count of UNESCO sites.

| Language | Records |
| --- | ---: |
| English | 1,155 |
| German | 1,105 |
| Japanese | 1,078 |
| Arabic | 577 |
| Hindi | 577 |
| French | 576 |
| Spanish | 571 |

The English records comprise 898 cultural, 218 natural, and 39 mixed sites. Multi-region sites participate in each of the five region filters. The import strips HTML, validates finite coordinates, treats source area zeros as missing, removes old comments and unattributed image links, and rejects duplicate translation keys. A SHA-256 checksum and exact counts live in [data/manifest.json](data/manifest.json).

Translations were machine generated during the original coursework and are **not independently reviewed**. Coverage varies. Internal `site_####` identifiers are not UNESCO inscription IDs. The original multi-gigabyte GridFS image archive is deliberately excluded; the shipped illustrations do not depict individual sites. [Provenance and attribution](docs/DATA_SOURCES.md).

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/sites` | Search with `q`, `language`, `category`, `region`, `lat`, `lon`, `radius`, `page`, `per_page` |
| `GET /api/sites/<site_id>?language=English` | A single translation; 404 when absent |
| `GET /api/metadata` | Unique sites, translation counts, available languages and regions |
| `GET /media/<site_id>` | GridFS raster image or illustration redirect |
| `GET /health/live` | Process liveness, independent of database availability |
| `GET /health/ready` | Database connection, nonempty dataset, and geospatial index readiness |

```sh
curl "http://localhost:5050/api/sites?q=temple&language=English&per_page=3"
curl "http://localhost:5050/api/sites?lat=48.85&lon=2.35&radius=100"
```

`radius` is in kilometres. All three geographic parameters are required together. Page size is capped at 48; queries have a three-second database execution budget. Errors use 400/404/503 with a JSON `error` object and request ID. All application routes are read-only. See [API details](docs/API.md).

## Engineering and verification

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/check.py -q
ruff check .
ruff format --check .
pip-audit -r requirements.txt
```

Run the native demo first. `scripts/check.py` reads the local credentials without printing them and creates a randomly named, isolated test database. It removes only that test database. Alternatively, supply `MONGO_TEST_URI` for your own test instance. Plain `pytest` skips database-dependent tests if this variable is absent.

Browser and accessibility checks:

```sh
npm ci
python -m playwright install chromium
python scripts/browser_check.py
npm run format:check
```

The suite covers real geospatial queries (including the international date line), pagination and totals, escaped regex input, translation lookup, import idempotence, image import/streaming/cache validation, safe HTML rendering, database outages, and readiness. Chromium exercises search, back navigation, Arabic content, private notes, empty/error states, mobile layouts, and blocked map tiles. Axe checks selected desktop/mobile pages; automated checks do not constitute a complete accessibility certification.

GitHub Actions runs these checks with native MongoDB 8.0.34 and Python 3.12. [Architecture](docs/ARCHITECTURE.md) · [Validation results](docs/VALIDATION.md) · [Career-fair walkthrough and resume bullets](docs/CAREER_FAIR.md).

## Design decisions and boundaries

Flask renders the interface and the JSON API uses the same validation and repository layer. MongoDB remains the source of truth. There is no frontend build requirement for running the app; npm is used only for development checks. Leaflet 1.9.4 is vendored with its license. OpenStreetMap is the only network dependency used by the browser during normal operation.

This is a tested portfolio application with a reproducible local deployment. A public production deployment still needs a hosting environment, HTTPS, monitored backups, and traffic controls. There is no public hosted demo or claim of production traffic. Literal substring search scans matching language records; this dataset does not justify claims about performance over millions of documents. See the [deployment notes](docs/OPERATIONS.md) for scaling and operational tradeoffs.
