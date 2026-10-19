import gzip
import hashlib
import json
from pathlib import Path

import pytest

from heritage.ingestion import load_records, normalize, plain_text

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_integrity_and_manifest():
    path = ROOT / "data/heritage.json.gz"
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    docs = load_records(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["sha256"]
    assert len(docs) == manifest["records"] == 5639
    assert len({d["site_id"] for d in docs}) == manifest["unique_sites"] == 1155
    assert all("image_id" not in d and "comments" not in d for d in docs)
    assert {d["language"] for d in docs} == set(manifest["languages"])


def test_strip_markup_and_decode_entities():
    assert plain_text("<p>World &amp; <b>heritage</b></p>") == "World & heritage"
    assert "<" not in plain_text("<script>alert(1)</script><img src=x onerror=alert(1)>")


def test_bad_dataset_fails_before_import(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('[{"site_id":"site_0001"}]')
    with pytest.raises((KeyError, ValueError)):
        load_records(path)


def test_duplicate_translations_rejected(tmp_path):
    with gzip.open(ROOT / "data/heritage.json.gz", "rt", encoding="utf-8") as f:
        doc = json.load(f)[0]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps([doc, doc]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_records(path)


def test_invalid_coordinates_rejected():
    with gzip.open(ROOT / "data/heritage.json.gz", "rt", encoding="utf-8") as f:
        doc = json.load(f)[0]
    doc["location"]["coordinates"] = [0, float("nan")]
    with pytest.raises(ValueError, match="coordinates"):
        normalize(doc)
