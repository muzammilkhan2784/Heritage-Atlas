# Career-fair kit

## Resume entry

**UNESCO World Heritage Explorer — Python, Flask, MongoDB, PyMongo, GridFS, Leaflet**

- Engineered a multilingual heritage explorer over **1,155 sites and 5,639 records across seven languages**, with validated data ingestion, a paginated REST API, and interactive geographic discovery.
- Implemented **MongoDB 2dsphere / `$geoNear` search** with distance-ranked results, composable filters, stable pagination, and GridFS image delivery with cache validation and safe fallbacks.
- Added **39 automated tests with 98% backend coverage**, native MongoDB/Python setup, GitHub Actions checks, and Chromium coverage of mobile layouts, Arabic content, saved notes, and failure states.

Two-bullet alternative for a tight resume:

- Built a Flask/MongoDB heritage atlas supporting **1,155 sites, 5,639 multilingual records, and seven languages**, with GeoJSON radius search, interactive maps, and a paginated REST API.
- Established validated imports, secure configuration, GridFS media handling, and CI; verified **39 tests with 98% backend coverage** plus desktop/mobile browser checks.

Use metrics only while they match the repository's validation results. Describe the collection as a historical snapshot, not the current UNESCO list. The application is tested locally; do not describe it as serving production users or claim a deployed public URL.

## 30-second explanation

“I built a World Heritage explorer that lets people search cultural and natural sites in seven languages and discover places near a location. The original challenge was turning inconsistent MongoDB records into something reliable: I normalized the data, enforced unique translation keys, added geospatial indexes, and made imports repeatable. The API and web interface share validation, and I tested actual MongoDB behavior, including distance ordering, missing translations, and database outages.”

## Two-minute demo

1. Start the native app with `Start-Demo.cmd`, then open `http://localhost:5050`. Point out the actual archive counts and the historical-data label.
2. Search **Angkor** and open its detail page. Explain how filters live in the URL and the back link restores the search.
3. Open `http://localhost:5050/view/site_0001`. Switch to **Arabic**. Point out the right-to-left content and the explicit machine-translation notice.
4. Save a private field note, reload, switch language, and show that the same site retains its note. Delete the note afterward.
5. Search around **48.85, 2.35**, radius **100 km**. Show distance ordering and map markers. Explain GeoJSON's longitude/latitude order.
6. Show the GitHub README, architecture diagram, CI result, and a test for crossing the international date line.

If venue internet is unavailable, the native app still serves the dataset, search, illustrations, and detail pages; map tiles may be unavailable. Open the app before leaving and keep the Python terminal running. Keep repository screenshots ready as a second demo option. A recruiter cannot access your `localhost` URL remotely; give them the GitHub repository link.

## Interview points

**Why MongoDB?** The documents combine multilingual text, representative GeoJSON locations, and optional media references. Native geospatial queries and GridFS preserve the original project's data-engineering focus.

**What makes the geospatial search correct?** Validate finite latitude/longitude/radius values, store coordinates longitude-first, filter inside `$geoNear`, calculate spherical distance, and paginate after distance sorting. A real MongoDB test verifies a query spanning longitude +179.9° to −179.9°.

**Why no public comments?** Anonymous comments require moderation and abuse controls. The explorer uses private device-local notes and keeps the server API read-only. This is a deliberate scope decision, not a claim of implementing authentication.

**How did you verify reliability?** Tests use an isolated real MongoDB database, validate the seed checksum and counts, repeat imports, verify missing/unsupported images, and exercise database outage responses. Chromium checks primary user flows and responsive widths, and axe checks selected pages for automated accessibility violations.

**What would you improve with more time?** Independently review translations, obtain attributed site photography, refresh and version the upstream dataset, add cursor pagination and indexed multilingual full-text search for a larger collection, then deploy behind HTTPS with traffic limits, backups, and monitoring.
