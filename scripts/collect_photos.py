"""Build an attributed photo collection from reviewed UNESCO/Wikidata associations.

The input plan maps internal site IDs to UNESCO inscription IDs and Commons files.
Requests are cached and bounded; rerunning resumes interrupted work.
"""

import argparse
import hashlib
import io
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {
    "User-Agent": "HeritageAtlas/1.0 (https://github.com/muzammilkhan2784/UNESCO-World-Heritage-Explorer)"
}
API = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENSES = (
    "CC BY",
    "CC0",
    "Public domain",
    "PDM",
    "CC-BY",
    "FAL",
    "Attribution",
    "CC SA",
    "Copyrighted free use",
    "Licence Ouverte",
    "KOGL Type 1",
    "GFDL",
)


def request_json(url, params):
    for attempt in range(4):
        response = requests.get(url, params=params, headers=HEADERS, timeout=40)
        if response.status_code in {429, 502, 503, 504}:
            time.sleep(min(20, 2**attempt * 2))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Remote source remained unavailable")


def file_title(url):
    return "File:" + unquote(url.rsplit("/", 1)[-1]).replace("_", " ")


def metadata_batch(titles, cache):
    key = hashlib.sha256("|".join(titles).encode()).hexdigest()
    path = cache / (key + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = request_json(
        API,
        {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime|mediatype",
            "iiurlwidth": 1280,
            "format": "json",
            "redirects": 1,
        },
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(0.15)
    return data


def usable(info, title):
    extra = info.get("extmetadata", {})
    license_name = extra.get("LicenseShortName", {}).get("value", "")
    if not license_name.startswith(ALLOWED_LICENSES):
        return False
    if info.get("mime") not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        return False
    if info.get("width", 0) < 250 or info.get("height", 0) < 180:
        return False
    return not re.search(r"\b(?:locator|location map|logo|flag of|coat of arms)\b", title.lower())


def download(row, candidate, output):
    from heritage.ingestion import plain_text

    site_id = row["site_id"]
    title, info = candidate
    extra = info["extmetadata"]
    path = output / f"{site_id}.webp"
    url = info.get("thumburl", info["url"]).split("?")[0]
    if urlparse(url).hostname not in {"upload.wikimedia.org", "thumb.wikimedia.org"}:
        raise ValueError("Unexpected media host")
    if not path.exists():
        response = None
        for attempt in range(4):
            response = requests.get(url, headers=HEADERS, timeout=50, stream=True)
            if response.status_code in {429, 502, 503, 504}:
                response.close()
                time.sleep(min(20, 2**attempt * 2))
                continue
            if not response.ok and attempt == 0:
                response.close()
                url = info["url"].split("?")[0]
                continue
            break
        with response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > 25_000_000:
                    raise ValueError("Image exceeds download limit")
        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1200, 900))
            image.save(path, "WEBP", quality=70, method=5)
    overrides_path = output / "attribution-overrides.json"
    overrides = (
        json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    )
    author = overrides.get(title.removeprefix("File:")) or plain_text(
        extra.get("Artist", {}).get(
            "value", "Photographer not named in source metadata; see source page"
        )
    )
    with Image.open(path) as image:
        width, height = image.size
    return {
        "site_id": site_id,
        "site_name": row["name"],
        "unesco_id": row["unesco_id"],
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": info["descriptionurl"],
        "original_url": info["url"].split("?")[0],
        "title": title.removeprefix("File:"),
        "author": author,
        "license": extra["LicenseShortName"]["value"],
        "license_url": extra.get("LicenseUrl", {})
        .get("value", info["descriptionurl"])
        .replace("http://", "https://"),
        "caption": plain_text(extra.get("ImageDescription", {}).get("value", row["name"])),
        "changes": "Resized and converted to WebP; page thumbnails are additionally resized.",
        "width": width,
        "height": height,
        "match": row["match"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "data/photos/sources.json")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    output = ROOT / "data/photos"
    cache = ROOT / "work/commons-metadata"
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    catalog_path = output / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    failures = {}
    candidates_by_title = {}
    # Fetch only the first two candidates initially; later runs can extend reviewed plans.
    titles = list(
        dict.fromkeys(
            file_title(url)
            for row in plan
            if row["site_id"] not in catalog
            for url in row["candidates"][:2]
        )
    )
    batches = [titles[i : i + 10] for i in range(0, len(titles), 10)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(metadata_batch, batch, cache): batch for batch in batches}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                for page in future.result().get("query", {}).get("pages", {}).values():
                    for info in page.get("imageinfo", []):
                        if usable(info, page["title"]):
                            candidates_by_title[page["title"]] = (page["title"], info)
            except Exception as exc:
                failures["metadata:" + str(i)] = type(exc).__name__
            if i % 20 == 0:
                print(f"Metadata batches {i}/{len(batches)}", flush=True)
    tasks = []
    for row in plan:
        if row["site_id"] in catalog:
            continue
        candidate = next(
            (
                candidates_by_title.get(file_title(url))
                for url in row["candidates"][:2]
                if file_title(url) in candidates_by_title
            ),
            None,
        )
        if candidate:
            tasks.append((row, candidate))
        else:
            failures[row["site_id"]] = "No licensed photographic candidate yet"
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, row, candidate, output): row for row, candidate in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                catalog[row["site_id"]] = future.result()
            except Exception as exc:
                failures[row["site_id"]] = type(exc).__name__ + (
                    ":" + str(exc.response.status_code)
                    if isinstance(exc, requests.HTTPError)
                    else ":" + str(exc)[:100]
                )
            if i % 20 == 0 or i == len(futures):
                catalog_path.write_text(
                    json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    f"Photos processed {i}/{len(futures)}; available {len(catalog)}/{len(plan)}",
                    flush=True,
                )
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "work/photo-failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    print(
        f"Completed with {len(catalog)} photos; {len(failures)} entries need follow-up.", flush=True
    )


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    main()
