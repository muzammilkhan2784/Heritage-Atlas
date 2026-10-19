"""One validation boundary shared by HTML and JSON searches."""

import math
from dataclasses import asdict, dataclass

LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Arabic": "ar",
    "Hindi": "hi",
}
CATEGORIES = ("Cultural", "Natural", "Mixed")


class InvalidSearch(ValueError):
    pass


@dataclass(frozen=True)
class Search:
    q: str = ""
    language: str = "English"
    category: str = ""
    region: str = ""
    lat: float | None = None
    lon: float | None = None
    radius: float | None = None
    page: int = 1
    per_page: int = 12

    def params(self):
        return {k: v for k, v in asdict(self).items() if v is not None and v != ""}


def parse_search(args):
    q = args.get("q", "").strip()
    language = args.get("language", "English")
    category = args.get("category", "")
    region = args.get("region", "").strip()
    if len(q) > 120 or len(region) > 100:
        raise InvalidSearch("Search text is too long (maximum 120 characters).")
    if language not in LANGUAGES:
        raise InvalidSearch("Choose a supported language.")
    if category and category not in CATEGORIES:
        raise InvalidSearch("Choose Cultural, Natural, or Mixed.")
    coords = [args.get(k, "").strip() for k in ("lat", "lon", "radius")]
    lat = lon = radius = None
    if any(coords):
        if not all(coords):
            raise InvalidSearch("Nearby search needs latitude, longitude, and a radius.")
        try:
            lat, lon, radius = map(float, coords)
        except ValueError as exc:
            raise InvalidSearch("Coordinates and radius must be numbers.") from exc
        if not all(map(math.isfinite, (lat, lon, radius))):
            raise InvalidSearch("Coordinates and radius must be finite numbers.")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180 or not 0 < radius <= 20000:
            raise InvalidSearch("Latitude: −90 to 90; longitude: −180 to 180; radius: 0–20,000 km.")
    try:
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", 12))
    except (TypeError, ValueError) as exc:
        raise InvalidSearch("Page and page size must be whole numbers.") from exc
    if not 1 <= page <= 1000 or not 1 <= per_page <= 48:
        raise InvalidSearch("Page must be 1–1,000 and page size 1–48.")
    return Search(q, language, category, region, lat, lon, radius, page, per_page)
