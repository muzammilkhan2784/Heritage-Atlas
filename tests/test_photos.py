import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from heritage.photos import import_catalog


def test_bundled_photos_cover_the_full_site_collection():
    import gzip

    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "data/photos/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    with gzip.open(root / "data/heritage.json.gz", "rt", encoding="utf-8") as source:
        sites = {d["site_id"] for d in json.load(source)}
    assert set(catalog) == sites
    for site_id, entry in catalog.items():
        payload = (catalog_path.parent / entry["file"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"], site_id
        assert entry["source"].startswith("https://")
        assert entry["license_url"].startswith("https://")
        assert entry["author"] and entry["license"]
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()


@pytest.fixture
def photo_catalog(tmp_path):
    path = tmp_path / "site_0001.webp"
    Image.new("RGB", (800, 600), "royalblue").save(path, "WEBP")
    entry = {
        "site_id": "site_0001",
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "author": "Test photographer",
        "license": "CC BY-SA 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:Test.webp",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    }
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"site_0001": entry}), encoding="utf-8")
    return catalog


def test_catalog_gridfs_variants_translation_links_and_idempotence(app, client, photo_catalog):
    repo = app.extensions["repository"]
    assert import_catalog(repo, photo_catalog) == 1
    assert repo.db["fs.files"].count_documents({}) == 2
    assert (
        repo.sites.count_documents(
            {"site_id": "site_0001", "image_thumbnail_id": {"$exists": True}}
        )
        == 2
    )
    full = client.get("/media/site_0001")
    thumb = client.get("/media/site_0001?size=thumb")
    assert full.mimetype == thumb.mimetype == "image/webp"
    with Image.open(io.BytesIO(thumb.data)) as image:
        assert image.width <= 440 and image.height <= 300
    assert full.headers["ETag"] != thumb.headers["ETag"]
    import_catalog(repo, photo_catalog)
    assert repo.db["fs.files"].count_documents({}) == 2
    assert "Test photographer" in client.get("/view/site_0001?lang=French").text
    assert client.get("/media/site_0001?size=huge").status_code == 400
    doc = repo.sites.find_one({"site_id": "site_0001"})
    repo.fs.delete(doc["image_thumbnail_id"])
    assert client.get("/media/site_0001?size=thumb").data == full.data


def test_catalog_rejects_corruption_before_writing(app, photo_catalog):
    image = photo_catalog.parent / "site_0001.webp"
    image.write_bytes(b"bad image")
    repo = app.extensions["repository"]
    with pytest.raises(ValueError, match="checksum"):
        import_catalog(repo, photo_catalog)
    assert repo.db["fs.files"].count_documents({}) == 0


def test_catalog_rejects_path_traversal_and_missing_credit(app, photo_catalog):
    catalog = json.loads(photo_catalog.read_text(encoding="utf-8"))
    catalog["site_0001"]["file"] = "../outside.webp"
    photo_catalog.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="inside"):
        import_catalog(app.extensions["repository"], photo_catalog)
    catalog["site_0001"]["file"] = "site_0001.webp"
    catalog["site_0001"]["author"] = ""
    photo_catalog.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="author"):
        import_catalog(app.extensions["repository"], photo_catalog)


def test_catalog_cli(app, photo_catalog):
    result = app.test_cli_runner().invoke(args=["import-photos", str(photo_catalog)])
    assert result.exit_code == 0, result.output
    photo_catalog.write_text("[]")
    result = app.test_cli_runner().invoke(args=["import-photos", str(photo_catalog)])
    assert result.exit_code != 0


def test_result_language_picker_only_lists_available_translations(client):
    response = client.get("/").text
    beta_picker = response.split('id="lang-site_0002"')[1].split("</select>")[0]
    assert "English" in beta_picker
    assert "French" not in beta_picker


def test_preserved_original_has_no_derived_thumbnail(app, client, photo_catalog):
    image_path = photo_catalog.parent / "original.jpg"
    Image.new("RGB", (800, 600), "green").save(image_path, "JPEG")
    catalog = json.loads(photo_catalog.read_text(encoding="utf-8"))
    entry = catalog["site_0001"]
    entry.update(
        file=image_path.name,
        sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
        preserve_original=True,
        changes="Original source file retained unchanged.",
    )
    photo_catalog.write_text(json.dumps(catalog))
    repo = app.extensions["repository"]
    import_catalog(repo, photo_catalog)
    assert repo.db["fs.files"].count_documents({}) == 1
    assert client.get("/media/site_0001").data == image_path.read_bytes()
    assert client.get("/media/site_0001?size=thumb").data == image_path.read_bytes()
    assert client.get("/media/site_0001").mimetype == "image/jpeg"


def test_operator_replacement_clears_old_thumbnail_and_survives_catalog_seed(
    app, client, photo_catalog
):
    repo = app.extensions["repository"]
    import_catalog(repo, photo_catalog)
    image_path = photo_catalog.parent / "replacement.jpg"
    Image.new("RGB", (700, 500), "red").save(image_path, "JPEG")
    result = app.test_cli_runner().invoke(
        args=[
            "import-image",
            "site_0001",
            str(image_path),
            "--credit",
            "Replacement author",
            "--source",
            "https://example.com/new-photo",
        ]
    )
    assert result.exit_code == 0, result.output
    assert client.get("/media/site_0001?size=thumb").data == image_path.read_bytes()
    assert import_catalog(repo, photo_catalog) == 0
    assert client.get("/media/site_0001").data == image_path.read_bytes()
    assert client.get("/api/sites/site_0001").json["image_credit"] == "Replacement author"
