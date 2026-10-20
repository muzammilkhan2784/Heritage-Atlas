# Running and maintaining UNESCO World Heritage Explorer

## Local demo

On Windows with Python installed, double-click `Start-Demo.cmd`. It creates a virtual environment if needed, installs the runtime requirements, generates credentials if missing, installs native MongoDB if missing, and launches the demo. The server stays in that terminal; Ctrl+C stops the web server and the MongoDB process it started.

Manual equivalent:

```sh
python -m venv .venv
# Activate the environment for your shell.
python -m pip install -r requirements.txt
python scripts/bootstrap.py
python scripts/install_mongodb.py
python scripts/run_local.py
```

The native installer supports Windows x64 and Ubuntu 24.04 x64. An independently installed `mongod` on PATH also works. It verifies the official archive SHA-256 before extraction. The launcher binds MongoDB to `127.0.0.1:27018`, with authentication enabled from startup. The localhost exception creates the first admin on a new database, then an authenticated admin creates the database-scoped application user. Flask/Waitress listens on `127.0.0.1:5050`.

Local files:

| Path | Purpose |
| --- | --- |
| `.env` | Random admin and application passwords, generated once |
| `.runtime/mongodb/` | Project-local MongoDB binaries and their upstream notices |
| `.runtime/data/` | Native MongoDB storage; persists between runs |
| `.runtime/mongod.log` | Database diagnostic log |
| `data/heritage.json.gz` | Portable, validated historical seed dataset |

`.env` and `.runtime/` are excluded from Git. Do not delete the data directory while MongoDB is running. The launcher does not open or modify the old coursework database, its WiredTiger files, or other applications' databases. On Ctrl+C, it requests an authenticated graceful database shutdown and waits before using a process termination fallback.

If port 27018 is occupied, the launcher refuses to attach to an unknown local process. Stop the other instance or set `MONGO_URI` to an explicitly selected existing database. If port 5050 is occupied, stop the previous demo before restarting. Authentication failures usually mean `.env` no longer matches the users stored in `.runtime/data`; restore the matching credentials rather than regenerating them.

## Existing MongoDB or Atlas

Set both variables in the shell used to launch the app:

```powershell
$env:MONGO_URI = 'mongodb://your-user:your-password@your-host:27017/your-db?authSource=your-db'
$env:MONGO_DB = 'your-db'
python scripts/run_local.py
```

For Atlas, use the cluster's supplied `mongodb+srv://` connection string, database user, network access rules, and TLS configuration. Keep real values outside source control and screenshots. The launcher will validate/import the bundled snapshot into the explicitly named database; use a dedicated database for this project. It will not start or stop an externally managed database.

For an independently managed server without automatic seeding on startup:

```sh
flask --app app:create_app init-db
flask --app app:create_app import-data data/heritage.json.gz
waitress-serve --host=127.0.0.1 --port=5050 --threads=8 --call app:create_app
```

The app does not load `.env` automatically. The native launcher uses it for its local credentials; a managed deployment injects `MONGO_URI` and `MONGO_DB` into the process environment.

## Importing attributed photography

The launcher imports the bundled photo catalog into GridFS automatically. Images and search thumbnails are shared across all translations of a site. File hashes are checked, identical variants are reused on repeated imports, custom operator images are retained, and attribution is stored with both site records and GridFS files. To import the catalog manually:

```sh
flask --app app:create_app import-photos data/photos/catalog.json
```

Two UNESCO originals marked as no-derivatives are served unchanged for both sizes. Other images use a full-size WebP and a smaller result thumbnail. To add another image you have rights to use:

```sh
flask --app app:create_app import-image site_0001 path/to/photo.jpg --credit "Author / license" --source "https://source-page.example/photo"
```

Run this in an environment with the intended MongoDB URI and database set. The command accepts JPEG, PNG, or WebP signatures up to 10 MB, requires an HTTPS attribution source, stores the file in GridFS, and links all translations. The source URL is recorded, not fetched by the server. Repeated imports create a new GridFS object; older objects remain available until an operator removes unreferenced media. This command is for trusted operators, not public uploads.

## Backup and migration

Use MongoDB's `mongodump`/`mongorestore` tools or a managed provider's snapshot process. Back up the application database, including `sites`, `fs.files`, and `fs.chunks`, and retain credentials through an appropriate secret manager. The repository can recreate the historical text and bundled photo collection, but it does not back up operator-added images or custom records. Periodically restore a backup into a separate database and verify readiness, counts, translations, and media before relying on it. Never copy live WiredTiger files as a substitute for a supported backup.

The database import validates the whole input before writing and upserts in batches of 500. It is idempotent by translation key but is not a full-dataset transaction. A failure during a write can leave partial progress; rerun the same import after recovery. It never prunes extra records or translates text at runtime.

## Public deployment

The current deliverable is a local demo and a GitHub repository. For public hosting, run Waitress as a managed unprivileged process behind an HTTPS reverse proxy, use a separately managed authenticated MongoDB instance, and restrict network access to the database. Inject secrets through the hosting platform, configure backups and alerting, apply request/connection limits at ingress, and set a log retention policy. Give web workers read-only database access where possible; keep index creation and imports under a separate operator credential.

Use `/health/ready` for readiness and `/health/live` for process liveness. Do not restart a healthy web process solely because MongoDB is temporarily unavailable. Requests carry correlation IDs, and logs exclude query strings and credentials. Add centralized metrics and tracing if operating beyond a portfolio deployment; this repository does not claim those integrations already exist.

The original Git history contains a classroom database credential. The new setup uses unrelated random credentials. If that original password is still active anywhere, rotate it there; editing source does not invalidate old credentials.

## Updating the data

To reproduce the portable snapshot from the original local export:

```sh
python scripts/prepare_dataset.py path/to/sites_merged.bson
```

Review the regenerated manifest and checksum, rerun data integrity and MongoDB tests, and inspect the interface. Update source attribution, language coverage, and any resume/documentation metrics when changing snapshots. A historical snapshot must not be presented as the current World Heritage List.
