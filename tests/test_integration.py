import pytest

from heritage import create_app
from heritage.ingestion import import_records
from heritage.validation import Search

pytestmark = pytest.mark.integration


def test_paginated_api_projection(client):
    result = client.get("/api/sites?per_page=2").json
    assert result["total"] == 4
    assert result["pages"] == 2
    assert [d["name"] for d in result["items"]] == ["Alpha temple", "Beta forest"]
    assert "_id" not in result["items"][0]
    assert len(client.get("/api/sites?page=2&per_page=2").json["items"]) == 2
    assert client.get("/api/sites?page=999").json["items"] == []


def test_literal_regex_and_case_insensitive_search(client):
    assert client.get("/api/sites?q=.*").json["total"] == 0
    assert client.get("/api/sites?q=TEMPLE").json["total"] == 1
    assert client.get("/api/sites?q=history").json["total"] == 4


def test_filters_are_composed(client):
    result = client.get("/api/sites?category=Natural&region=Test%20region").json
    assert result["total"] == 1
    assert result["items"][0]["site_id"] == "site_0002"
    assert client.get("/api/sites?language=French").json["total"] == 1


def test_geospatial_distance_order_and_total(client):
    result = client.get("/api/sites?lat=48.85&lon=2.35&radius=5&per_page=1").json
    assert result["total"] == 2
    assert result["items"][0]["name"] == "Alpha temple"
    assert result["items"][0]["distance_m"] < 1
    second = client.get("/api/sites?lat=48.85&lon=2.35&radius=5&per_page=1&page=2").json
    assert 1000 < second["items"][0]["distance_m"] < 2000


def test_geospatial_crosses_antimeridian(client):
    result = client.get("/api/sites?lat=0&lon=179.9&radius=30").json
    assert result["total"] == 1
    assert result["items"][0]["name"] == "Dateline"


def test_validation_error_contract(client):
    response = client.get("/api/sites?lat=nan&lon=0&radius=100")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_search"
    assert response.json["error"]["request_id"] == response.headers["X-Request-ID"]
    assert client.get("/?page=-1").status_code == 400


def test_detail_translation_and_missing_site(client):
    assert client.get("/view/site_0001?lang=French").status_code == 200
    assert client.get("/api/sites/site_0001?language=French").json["name"] == "Temple traduit"
    assert client.get("/view/site_0002?lang=French").status_code == 404
    assert client.get("/api/sites/missing").status_code == 404
    assert client.get("/api/sites/site_0001?language=bad").status_code == 400


def test_html_escapes_content_and_map_payload(app, client):
    app.extensions["repository"].sites.update_one(
        {"site_id": "site_0001", "language": "English"},
        {"$set": {"name": '</script><script>alert("x")</script>'}},
    )
    body = client.get("/").text
    assert '</script><script>alert("x")</script>' not in body
    assert "\\u003c/script\\u003e" in body


def test_media_fallback_and_gridfs_stream(app, client):
    assert client.get("/media/site_0001").status_code == 302
    repo = app.extensions["repository"]
    payload = b"\xff\xd8\xfftest-image"
    image = repo.fs.put(payload, filename="test.jpg", metadata={"content_type": "image/jpeg"})
    repo.sites.update_one({"site_id": "site_0001"}, {"$set": {"image_id": image}})
    response = client.get("/media/site_0001")
    assert response.status_code == 200
    assert response.data == payload
    assert response.mimetype == "image/jpeg"
    assert (
        client.get(
            "/media/site_0001", headers={"If-None-Match": response.headers["ETag"]}
        ).status_code
        == 304
    )
    repo.fs.delete(image)
    assert client.get("/media/site_0001").status_code == 302


def test_reject_unsafe_gridfs_content(app, client):
    repo = app.extensions["repository"]
    image = repo.fs.put(b"<svg></svg>", metadata={"content_type": "image/svg+xml"})
    repo.sites.update_one({"site_id": "site_0001"}, {"$set": {"image_id": image}})
    assert client.get("/media/site_0001").status_code == 302


def test_repeat_import_preserves_unique_records(app):
    repo = app.extensions["repository"]
    docs = list(repo.sites.find({}, {"_id": 0}))
    import_records(repo, docs)
    import_records(repo, docs)
    assert repo.sites.count_documents({}) == 5
    assert repo.search(Search()).get("total") == 4


def test_metadata_health_headers_and_read_only_api(client):
    assert client.get("/api/metadata").json["sites"] == 4
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.post("/view/site_0001", data={"comment": "spam"}).status_code == 405
    assert client.post("/api/sites", json={"name": "spam"}).status_code == 405


def test_outage_does_not_break_liveness_or_leak_credentials():
    application = create_app(
        {"TESTING": True, "MONGO_URI": "mongodb://unavailable:secret@127.0.0.1:1"}
    )
    client = application.test_client()
    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text
    assert client.get("/api/sites").status_code == 503
    assert client.get("/").status_code == 503
    application.extensions["mongo"].close()
