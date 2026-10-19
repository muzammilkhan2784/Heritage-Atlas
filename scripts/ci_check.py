"""Run CI against a native MongoDB process on an ephemeral runner."""

import os
import subprocess
import sys
import time
from pathlib import Path

from install_mongodb import binary
from pymongo import MongoClient
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parents[1]


def main():
    runtime = ROOT / ".runtime"
    data = runtime / "ci-data"
    data.mkdir(parents=True, exist_ok=True)
    executable = binary()
    if executable is None:
        raise SystemExit("Install native MongoDB first.")
    process = subprocess.Popen(
        [
            str(executable),
            "--bind_ip",
            "127.0.0.1",
            "--port",
            "27017",
            "--dbpath",
            str(data),
            "--logpath",
            str(runtime / "ci-mongod.log"),
        ]
    )
    env = os.environ.copy()
    env.update(
        MONGO_TEST_URI="mongodb://127.0.0.1:27017",
        MONGO_URI="mongodb://127.0.0.1:27017/heritage_ci",
        MONGO_DB="heritage_ci",
    )
    client = MongoClient(env["MONGO_TEST_URI"], serverSelectionTimeoutMS=500)
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Native MongoDB exited")
            try:
                client.admin.command("ping")
                break
            except PyMongoError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Native MongoDB did not become ready")
        for args in [
            ["scripts/check.py", "-q"],
            ["-m", "flask", "--app", "app:create_app", "import-data", "data/heritage.json.gz"],
            ["-m", "flask", "--app", "app:create_app", "import-photos", "data/photos/catalog.json"],
            ["scripts/browser_check.py", "--start-server"],
        ]:
            subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)
    finally:
        client.close()
        process.terminate()
        process.wait(timeout=15)


if __name__ == "__main__":
    main()
