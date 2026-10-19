"""Start authenticated native MongoDB, seed the archive, and serve Flask with Waitress.

Ctrl+C stops the web server and the MongoDB process started by this launcher.
Set MONGO_URI to use an independently managed MongoDB instance instead.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError
from waitress import serve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install_mongodb import binary  # noqa: E402

from heritage import create_app  # noqa: E402
from heritage.ingestion import import_records, load_records  # noqa: E402


def main():
    process = None
    admin_uri = None
    try:
        if not os.environ.get("MONGO_URI"):
            executable = binary()
            if executable is None:
                raise SystemExit("Run python scripts/install_mongodb.py first.")
            env_path = ROOT / ".env"
            if not env_path.exists():
                subprocess.run([sys.executable, str(ROOT / "scripts/bootstrap.py")], check=True)
            values = dict(
                line.split("=", 1)
                for line in env_path.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            port = 27018
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise SystemExit(
                        "Port 27018 is in use. Stop the existing instance or set MONGO_URI."
                    )
            runtime = ROOT / ".runtime"
            data = runtime / "data"
            data.mkdir(parents=True, exist_ok=True)
            command = [
                str(executable),
                "--bind_ip",
                "127.0.0.1",
                "--port",
                str(port),
                "--dbpath",
                str(data),
                "--logpath",
                str(runtime / "mongod.log"),
                "--logappend",
                "--auth",
            ]
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.Popen(command, creationflags=flags)
            local = MongoClient(f"mongodb://127.0.0.1:{port}", serverSelectionTimeoutMS=500)
            for _ in range(60):
                if process.poll() is not None:
                    raise SystemExit("MongoDB exited; inspect .runtime/mongod.log")
                try:
                    local.admin.command("ping")
                    break
                except PyMongoError:
                    time.sleep(0.5)
            else:
                raise SystemExit("MongoDB did not become ready; inspect .runtime/mongod.log")
            # On a new database, MongoDB's localhost exception permits creating the first admin.
            try:
                local.admin.command(
                    "createUser",
                    "heritage-admin",
                    pwd=values["MONGO_ROOT_PASSWORD"],
                    roles=["root"],
                )
            except OperationFailure as exc:
                if exc.code not in {13, 51003}:  # Existing authenticated database / existing user.
                    raise
            finally:
                local.close()
            admin_uri = f"mongodb://heritage-admin:{values['MONGO_ROOT_PASSWORD']}@127.0.0.1:{port}/?authSource=admin"
            with MongoClient(admin_uri, serverSelectionTimeoutMS=3000) as admin:
                users = admin.heritage.command("usersInfo", "mongoapp")["users"]
                if not users:
                    admin.heritage.command(
                        "createUser",
                        "mongoapp",
                        pwd=values["MONGO_APP_PASSWORD"],
                        roles=[{"role": "readWrite", "db": "heritage"}],
                    )
            os.environ["MONGO_URI"] = (
                f"mongodb://mongoapp:{values['MONGO_APP_PASSWORD']}@127.0.0.1:{port}/heritage?authSource=heritage"
            )
            os.environ["MONGO_DB"] = "heritage"
        app = create_app()
        repo = app.extensions["repository"]
        import_records(repo, load_records(ROOT / "data/heritage.json.gz"))
        print("Heritage Atlas is ready at http://127.0.0.1:5050", flush=True)
        print("Native MongoDB + Python / Waitress. Press Ctrl+C to stop.", flush=True)
        serve(app, host="127.0.0.1", port=5050, threads=8)
    except KeyboardInterrupt:
        print("Stopping Heritage Atlas.")
    except PyMongoError as exc:
        # Do not print connection strings or authentication exception details.
        raise SystemExit(
            f"MongoDB setup failed ({type(exc).__name__}). "
            "Check credentials and .runtime/mongod.log."
        ) from None
    finally:
        if process is not None and process.poll() is None:
            if admin_uri:
                try:
                    with MongoClient(admin_uri, serverSelectionTimeoutMS=1000) as shutdown_client:
                        shutdown_client.admin.command("shutdown")
                except PyMongoError:
                    pass  # A successful MongoDB shutdown closes the connection.
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
