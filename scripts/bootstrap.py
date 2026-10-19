"""Create native MongoDB credentials once. Existing .env files are never overwritten."""

import secrets
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".env"
try:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(f"MONGO_ROOT_PASSWORD={secrets.token_hex(24)}\n")
        handle.write(f"MONGO_APP_PASSWORD={secrets.token_hex(24)}\n")
    print("Created .env with random local credentials. Run: python scripts/run_local.py")
except FileExistsError:
    print("Keeping existing .env. Run: python scripts/run_local.py")
