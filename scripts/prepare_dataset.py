"""Convert the original local BSON export into a safe, portable dataset.

Usage: python scripts/prepare_dataset.py path/to/sites_merged.bson
No original IDs, comments, credentials, or unattributed image references are exported.
"""

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from bson import decode_file_iter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from heritage.ingestion import normalize  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/heritage.json.gz"))
    args = parser.parse_args()
    with args.source.open("rb") as handle:
        docs = [normalize(row) for row in decode_file_iter(handle)]
    docs.sort(key=lambda d: (d["site_id"], d["language"]))
    payload = json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(payload, mtime=0))
    manifest = {
        "records": len(docs),
        "unique_sites": len({d["site_id"] for d in docs}),
        "languages": dict(sorted(Counter(d["language"] for d in docs).items())),
        "categories_english": dict(
            sorted(Counter(d["category"] for d in docs if d["language"] == "English").items())
        ),
        "inscription_year_range": [min(d["year"] for d in docs), max(d["year"] for d in docs)],
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "source": (
            "Original ISTE 438 coursework MongoDB export; "
            "historical Kaggle UNESCO Heritage Sites 2021 snapshot."
        ),
        "transformations": [
            "Strip HTML to plain text",
            "Validate finite WGS84 coordinates",
            "Normalize field names",
            "Split multi-region membership and treat source area zeros as missing",
            "Remove original BSON IDs, comments, and unattributed image links",
        ],
        "limitations": [
            "Historical snapshot, not the current UNESCO list",
            "Machine translations are incomplete and have not been independently reviewed",
            "Internal site IDs are not UNESCO inscription IDs",
        ],
    }
    args.output.with_name("manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
