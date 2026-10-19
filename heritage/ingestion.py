"""Validated, repeatable imports; no download or translation services at runtime."""

import gzip
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path

import click
from flask import current_app
from pymongo import UpdateOne

from heritage.validation import CATEGORIES, LANGUAGES


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(str(value))
    return " ".join(" ".join(parser.parts).split())


def normalize(row):
    def pick(new, old, default=""):
        return row.get(new, row.get(old, default))

    site_id = str(row["site_id"])
    language = row.get("language", "English")
    if not re.fullmatch(r"site_\d{4,6}", site_id) or language not in LANGUAGES:
        raise ValueError("Invalid site identifier or language")
    name = plain_text(pick("name", "Name"))
    category = pick("category", "category_long")
    year = int(pick("year", "date_inscribed"))
    if not name or len(name) > 1000 or category not in CATEGORIES or not 1978 <= year <= 2100:
        raise ValueError("Invalid name, category, or inscription year")
    if "location" in row:
        lon, lat = map(float, row["location"]["coordinates"])
    else:
        lon, lat = float(row["longitude"]), float(row["latitude"])
    area_raw = row.get("area_hectares")
    area = None if area_raw in (None, "", "NA") else float(area_raw)
    if (
        not all(math.isfinite(v) for v in (lat, lon))
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        raise ValueError("Invalid coordinates")
    if area is not None and (not math.isfinite(area) or area < 0):
        raise ValueError("Invalid area")
    if area == 0:
        area = None  # Source zeros do not reliably distinguish missing area from a measured zero.
    regions = [r.strip() for r in plain_text(pick("region", "Region")).split(",") if r.strip()]
    return {
        "site_id": site_id,
        "language": language,
        "name": name,
        "description": plain_text(pick("description", "short_description")),
        "year": year,
        "category": category,
        "country": plain_text(pick("country", "Country name")),
        "region": ", ".join(regions),
        "regions": regions,
        "area_hectares": area,
        "location": {"type": "Point", "coordinates": [lon, lat]},
        "translation_note": "Original English record"
        if language == "English"
        else "Machine translation from the original coursework; not independently reviewed.",
    }


def load_records(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError("Dataset must be a JSON array")
    if not all(isinstance(row, dict) for row in raw):
        raise ValueError("Each dataset record must be an object")
    # Validate everything before the first write. Duplicate translations are rejected.
    docs = [normalize(row) for row in raw]
    keys = [(d["site_id"], d["language"]) for d in docs]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate (site_id, language) records")
    return docs


def import_records(repo, docs):
    repo.init_indexes()
    operations = [
        UpdateOne({"site_id": d["site_id"], "language": d["language"]}, {"$set": d}, upsert=True)
        for d in docs
    ]
    for start in range(0, len(operations), 500):
        repo.sites.bulk_write(operations[start : start + 500], ordered=False)
    repo._metadata = None


def register_commands(app):
    @app.cli.command("import-photos")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    def import_photos(path):
        """Import an attributed photo catalog and result thumbnails into GridFS."""
        from heritage.photos import import_catalog

        try:
            count = import_catalog(current_app.extensions["repository"], path)
        except (ValueError, KeyError, OSError) as exc:
            raise click.ClickException(f"Photo import failed: {exc}") from exc
        click.echo(f"Linked {count:,} site photos and thumbnails in GridFS.")

    @app.cli.command("init-db")
    def init_db():
        """Create indexes explicitly, outside the web worker startup path."""
        current_app.extensions["repository"].init_indexes()
        click.echo("Indexes ready.")

    @app.cli.command("import-data")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    def import_data(path):
        """Upsert a normalized JSON or JSON.gz dataset without deleting existing records."""
        try:
            docs = load_records(path)
        except (ValueError, KeyError, TypeError) as exc:
            raise click.ClickException(f"Dataset validation failed: {exc}") from exc
        import_records(current_app.extensions["repository"], docs)
        click.echo(
            f"Imported {len(docs):,} language records. Existing records were updated by key."
        )

    @app.cli.command("import-image")
    @click.argument("site_id")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option("--credit", required=True, help="Author and license attribution for this image.")
    @click.option(
        "--source", required=True, help="HTTPS source page identifying the image and license."
    )
    def import_image(site_id, path, credit, source):
        """Attach an attributed raster image to every translation of an existing site."""
        repo = current_app.extensions["repository"]
        if not repo.sites.find_one({"site_id": site_id}):
            raise click.ClickException("Unknown site identifier")
        content = Path(path).read_bytes()
        mime = (
            "image/jpeg"
            if content.startswith(b"\xff\xd8\xff")
            else "image/png"
            if content.startswith(b"\x89PNG\r\n\x1a\n")
            else "image/webp"
            if content[:4] == b"RIFF" and content[8:12] == b"WEBP"
            else None
        )
        if mime is None or len(content) > 10_000_000 or not source.startswith("https://"):
            raise click.ClickException(
                "Use JPEG, PNG, or WebP under 10 MB and an HTTPS source page"
            )
        image_id = repo.fs.put(
            content,
            filename=Path(path).name,
            metadata={"credit": credit, "source": source, "content_type": mime},
        )
        repo.sites.update_many(
            {"site_id": site_id},
            {"$set": {"image_id": image_id, "image_credit": credit, "image_source": source}},
        )
        click.echo(f"Image linked to {site_id}.")
