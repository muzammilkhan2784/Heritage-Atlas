import os
import uuid

import pytest
from pymongo import MongoClient

from heritage import create_app
from heritage.ingestion import import_records, normalize


@pytest.fixture(scope="session")
def database():
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        pytest.skip("Set MONGO_TEST_URI to run real MongoDB integration tests")
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    name = "heritage_test_" + uuid.uuid4().hex
    yield client[name]
    # Only this randomly named test database is removed; never the configured application DB.
    client.drop_database(name)
    client.close()


@pytest.fixture
def app(database):
    application = create_app(
        {"TESTING": True, "MONGO_URI": os.environ["MONGO_TEST_URI"], "MONGO_DB": database.name}
    )
    repo = application.extensions["repository"]
    repo.sites.delete_many({})
    database["fs.files"].delete_many({})
    database["fs.chunks"].delete_many({})
    docs = [
        {
            "site_id": "site_0001",
            "Name": "Alpha temple",
            "language": "English",
            "latitude": 48.85,
            "longitude": 2.35,
        },
        {
            "site_id": "site_0002",
            "Name": "Beta forest",
            "language": "English",
            "latitude": 48.86,
            "longitude": 2.36,
            "category_long": "Natural",
        },
        {
            "site_id": "site_0003",
            "Name": "Far away",
            "language": "English",
            "latitude": 13.4125,
            "longitude": 103.8667,
        },
        {
            "site_id": "site_0001",
            "Name": "Temple traduit",
            "language": "French",
            "latitude": 48.85,
            "longitude": 2.35,
        },
        {
            "site_id": "site_0004",
            "Name": "Dateline",
            "language": "English",
            "latitude": 0,
            "longitude": -179.9,
        },
    ]
    for d in docs:
        d.setdefault("category_long", "Cultural")
        d.update(
            short_description="<p>A history of people &amp; place.</p>",
            date_inscribed=1980,
            Region="Test region",
            area_hectares=42,
            **{"Country name": "Test country"},
        )
    import_records(repo, [normalize(d) for d in docs])
    yield application
    application.extensions["mongo"].close()


@pytest.fixture
def client(app):
    return app.test_client()
