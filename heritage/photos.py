"""Import attributed site photographs and small result thumbnails into MongoDB GridFS."""

import hashlib
import io
import json
import re
from pathlib import Path

from PIL import Image


def import_catalog(repo, path):
    path = Path(path)
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("Photo catalog must be an object keyed by site ID")
    validated = []
    # Check every file and attribution before changing the database.
    for site_id, entry in catalog.items():
        if not re.fullmatch(r"site_\d{4,6}", site_id) or entry.get("site_id") != site_id:
            raise ValueError("Invalid photo site identifier")
        image_path = (path.parent / entry["file"]).resolve()
        if image_path.parent != path.parent.resolve():
            raise ValueError("Photo file must stay inside its catalog directory")
        content = image_path.read_bytes()
        if len(content) > 10_000_000 or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"Photo checksum or size failed for {site_id}")
        with Image.open(io.BytesIO(content)) as image:
            original_jpeg = entry.get("preserve_original") and image.format == "JPEG"
            if (
                image.format != "WEBP" and not original_jpeg
            ) or image.width * image.height > 24_000_000:
                raise ValueError("Use WebP or an explicitly preserved original JPEG under 24 MP")
            image.verify()
        for key in ("author", "license", "source", "license_url"):
            if not entry.get(key):
                raise ValueError(f"Photo {site_id} is missing {key}")
        if not all(entry[key].startswith("https://") for key in ("source", "license_url")):
            raise ValueError("Photo attribution links must use HTTPS")
        validated.append((site_id, entry, content))

    known_sites = set(repo.sites.distinct("site_id"))
    if not set(catalog).issubset(known_sites):
        raise ValueError("Photo catalog includes unknown site IDs")
    files = repo.db["fs.files"]
    files.create_index([("metadata.asset_sha256", 1), ("metadata.variant", 1)])
    existing = {
        (d["metadata"]["asset_sha256"], d["metadata"]["variant"]): d["_id"]
        for d in files.find({"metadata.pipeline": "photos-v1"}, {"metadata": 1})
    }
    custom_sites = set(repo.sites.distinct("site_id", {"image_origin": "operator"}))
    linked_count = 0
    for site_id, entry, content in validated:
        if site_id in custom_sites:
            continue
        linked = {}
        for variant in ("full", "thumb"):
            if variant == "thumb" and entry.get("preserve_original"):
                linked[variant] = linked["full"]
                continue
            key = (entry["sha256"], variant)
            if key not in existing:
                payload = content
                if variant == "thumb":
                    with Image.open(io.BytesIO(content)) as image:
                        image.thumbnail((440, 300))
                        buffer = io.BytesIO()
                        image.save(buffer, "WEBP", quality=72, method=4)
                        payload = buffer.getvalue()
                existing[key] = repo.fs.put(
                    payload,
                    filename=f"{site_id}-{variant}{Path(entry['file']).suffix}",
                    metadata={
                        "content_type": "image/jpeg"
                        if entry.get("preserve_original")
                        else "image/webp",
                        "pipeline": "photos-v1",
                        "asset_sha256": entry["sha256"],
                        "variant": variant,
                        "author": entry["author"],
                        "license": entry["license"],
                        "license_url": entry["license_url"],
                        "source": entry["source"],
                        "changes": entry.get("changes", "Resized and converted to WebP"),
                    },
                )
            else:
                files.update_one(
                    {"_id": existing[key]},
                    {
                        "$set": {
                            "metadata.author": entry["author"],
                            "metadata.license": entry["license"],
                            "metadata.license_url": entry["license_url"],
                            "metadata.source": entry["source"],
                            "metadata.changes": entry.get(
                                "changes", "Resized and converted to WebP"
                            ),
                        }
                    },
                )
            linked[variant] = existing[key]
        repo.sites.update_many(
            {"site_id": site_id},
            {
                "$set": {
                    "image_id": linked["full"],
                    "image_thumbnail_id": linked["thumb"],
                    "image_credit": f"{entry['author']} / {entry['license']}",
                    "image_source": entry["source"],
                    "image_license_url": entry["license_url"],
                    "image_sha256": entry["sha256"],
                    "image_unesco_id": entry.get("unesco_id"),
                    "image_changes": entry.get("changes", "Resized and converted to WebP"),
                    "image_preserve_original": bool(entry.get("preserve_original")),
                    "image_origin": "catalog",
                }
            },
        )
        linked_count += 1
    repo._metadata = None
    return linked_count
