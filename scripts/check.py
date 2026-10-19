"""Run the full real-database suite using local .env credentials, without printing them."""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
if "MONGO_TEST_URI" not in env:
    values = dict(
        line.split("=", 1)
        for line in (root / ".env").read_text().splitlines()
        if line and not line.startswith("#")
    )
    env["MONGO_TEST_URI"] = (
        f"mongodb://heritage-admin:{values['MONGO_ROOT_PASSWORD']}@127.0.0.1:27018/?authSource=admin"
    )
raise SystemExit(
    subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=heritage",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            *sys.argv[1:],
        ],
        cwd=root,
        env=env,
    )
)
