# Verification record — 2026-10-19

Verified locally on Windows with **Python 3.10.11, native MongoDB Community 8.0.34, PyMongo 4.18.3, Flask 3.1.3, and Waitress 3.0.2**. The database ran directly on the PC with authentication, in its own project-local data directory.

| Check | Result |
| --- | --- |
| Automated Python suite against real MongoDB | **39 passed**, no skipped tests |
| Backend statement coverage | **98.03%** (299 of 305 statements) |
| Repository and query-validation modules | **100%** statement coverage |
| Ruff lint and Python formatting | Passed |
| Prettier CSS/JavaScript formatting | Passed |
| Runtime dependency audit | No known vulnerabilities reported by `pip-audit` at verification time |
| Chromium user flows | Passed; zero page JavaScript errors |
| Automated axe WCAG A/AA checks | Zero violations on eight selected desktop/mobile page cases |
| 390px search/detail layout | No horizontal overflow detected |
| Historical data integrity | 1,155 sites; 5,639 translations; SHA-256 matches manifest |

The Python suite exercises actual MongoDB, including geospatial order and totals, antimeridian distance, filter composition, literal regex input, stable pagination, translation lookup, JSON projections, escaped HTML/JSON, image import and GridFS streaming, conditional image requests, missing files, rejected media, idempotent imports, readiness checks, and database outages. Operator commands are tested through Flask's CLI runner. Tests create and remove an isolated randomly named database, not the application database.

The browser checks cover map markers, keyword search, result/detail/back navigation, nearby searches, Arabic content, note persistence across translations, note deletion, empty/error states, responsive widths, and blocked map tiles. The axe cases cover the home page, English detail, Arabic detail, and empty results at 1440px and 390px widths. Manual visual inspection checked desktop and mobile search/detail screenshots. Axe cannot assess every accessibility requirement; its incomplete checks still require human judgment.

## Small native HTTP timing sample

`python scripts/benchmark.py` made 100 requests at concurrency 8 after warm-up, rotating between browsing, keyword search, geographic search, and Japanese records:

| Measurement | Observed |
| --- | ---: |
| Successful responses | 100 / 100 |
| Median latency | 12.54 ms |
| 95th-percentile latency | 36.73 ms |
| Total sample time | 0.21 seconds |

This is a short sample on the developer's Windows machine with a local database and warm cache. It is not a production capacity test, availability promise, or externally measured service latency. Numbers vary with hardware and other workloads. The resume kit uses functional and test metrics rather than extrapolating these timings.

## Reproduction

Start the native app, install development requirements and npm tools, then run:

```sh
python scripts/check.py -q
ruff check .
ruff format --check .
npm run format:check
pip-audit -r requirements.txt
python scripts/browser_check.py
python scripts/benchmark.py
```

Browser reports/screenshots, the accessibility report, and timing samples are saved under ignored `work/`. GitHub Actions also passed on Ubuntu 24.04 / Python 3.12 using a native MongoDB process and uploaded browser artifacts. A local restart against the persistent Windows database also succeeded. The workflow's actual run status is available through the README badge and the repository Actions page.

## Remaining boundaries

The app has no public hosted deployment, reviewed human translations, bundled site photographs, public comments/authentication, centralized observability integration, or evidence of production traffic. Public operation needs the hosting and operational measures described in [OPERATIONS.md](OPERATIONS.md). Data is historical through 2021. These are explicit project boundaries, not features implied by the verification results.
