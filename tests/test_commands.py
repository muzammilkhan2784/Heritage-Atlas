import json

from heritage.ingestion import load_records


def test_init_and_import_commands(app, tmp_path):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    repo = app.extensions["repository"]
    path = tmp_path / "sites.json"
    docs = list(repo.sites.find({}, {"_id": 0}))
    path.write_text(json.dumps(docs), encoding="utf-8")
    assert runner.invoke(args=["import-data", str(path)]).exit_code == 0
    assert repo.sites.count_documents({}) == 5
    path.write_text('[{"site_id":"bad"}]')
    result = runner.invoke(args=["import-data", str(path)])
    assert result.exit_code != 0
    assert "validation failed" in result.output
    assert repo.sites.count_documents({}) == 5


def test_attributed_image_import_and_rejected_payloads(app, client, tmp_path):
    runner = app.test_cli_runner()
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xfftest-image")
    args = ["--credit", "Test author / CC0", "--source", "https://example.com/photo"]
    result = runner.invoke(args=["import-image", "site_0001", str(image), *args])
    assert result.exit_code == 0, result.output
    assert client.get("/media/site_0001").mimetype == "image/jpeg"
    assert client.get("/api/sites/site_0001").json["image_credit"] == "Test author / CC0"
    assert "Test author / CC0" in client.get("/view/site_0001").text
    assert runner.invoke(args=["import-image", "site_9999", str(image), *args]).exit_code != 0
    image.write_bytes(b"<html>not an image</html>")
    assert runner.invoke(args=["import-image", "site_0001", str(image), *args]).exit_code != 0


def test_readiness_checks_dataset_and_indexes(app, client):
    repo = app.extensions["repository"]
    repo.sites.drop_index("location_2dsphere")
    assert client.get("/health/ready").json["reason"] == "indexes_not_created"
    repo.sites.delete_many({})
    assert client.get("/health/ready").json["reason"] == "dataset_not_loaded"


def test_multiregion_membership(app):
    repo = app.extensions["repository"]
    from heritage.ingestion import normalize
    from heritage.validation import Search

    doc = repo.sites.find_one({"site_id": "site_0001", "language": "English"})
    doc["region"] = "Test region,Other region"
    doc = normalize(doc)
    repo.sites.update_one({"site_id": doc["site_id"], "language": "English"}, {"$set": doc})
    assert repo.search(Search(region="Test region"))["total"] == 4
    assert repo.search(Search(region="Other region"))["total"] == 1


def test_invalid_record_type(tmp_path):
    import pytest

    path = tmp_path / "bad.json"
    path.write_text("[null]")
    with pytest.raises(ValueError, match="record must be an object"):
        load_records(path)
