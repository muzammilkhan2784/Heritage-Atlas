"""MongoDB persistence. Bounded searches with explicit projections."""

import re
import time

import gridfs
from pymongo import ASCENDING, GEOSPHERE

PUBLIC_FIELDS = {
    "_id": 0,
    "site_id": 1,
    "language": 1,
    "name": 1,
    "description": 1,
    "year": 1,
    "category": 1,
    "region": 1,
    "country": 1,
    "area_hectares": 1,
    "location": 1,
    "distance_m": 1,
    "translation_note": 1,
    "image_credit": 1,
    "image_source": 1,
}


class Repository:
    def __init__(self, db):
        self.db = db
        self.sites = db.sites
        self.fs = gridfs.GridFS(db)
        self._metadata = None
        self._cached_at = 0

    def init_indexes(self):
        self.sites.create_index([("site_id", ASCENDING), ("language", ASCENDING)], unique=True)
        self.sites.create_index([("location", GEOSPHERE)])
        self.sites.create_index([("language", 1), ("category", 1), ("name", 1), ("site_id", 1)])
        self.sites.create_index([("language", 1), ("name", 1), ("site_id", 1)])

    def search(self, search):
        query = {"language": search.language}
        if search.q:
            pattern = {"$regex": re.escape(search.q), "$options": "i"}
            query["$or"] = [{"name": pattern}, {"description": pattern}]
        if search.category:
            query["category"] = search.category
        if search.region:
            query["regions"] = search.region
        if search.lat is not None:
            pipeline = [
                {
                    "$geoNear": {
                        "near": {"type": "Point", "coordinates": [search.lon, search.lat]},
                        "key": "location",
                        "distanceField": "distance_m",
                        "spherical": True,
                        "maxDistance": search.radius * 1000,
                        "query": query,
                    }
                },
                {"$sort": {"distance_m": 1, "site_id": 1}},
            ]
        else:
            pipeline = [{"$match": query}, {"$sort": {"name": 1, "site_id": 1}}]
        pipeline.append(
            {
                "$facet": {
                    "items": [
                        {"$skip": (search.page - 1) * search.per_page},
                        {"$limit": search.per_page},
                        {"$project": PUBLIC_FIELDS},
                    ],
                    "count": [{"$count": "total"}],
                }
            }
        )
        result = next(self.sites.aggregate(pipeline, maxTimeMS=3000))
        total = result["count"][0]["total"] if result["count"] else 0
        return {
            "items": result["items"],
            "total": total,
            "page": search.page,
            "per_page": search.per_page,
            "pages": (total + search.per_page - 1) // search.per_page,
        }

    def detail(self, site_id, language):
        return self.sites.find_one(
            {"site_id": site_id, "language": language}, PUBLIC_FIELDS, max_time_ms=3000
        )

    def languages(self, site_id):
        return sorted(self.sites.distinct("language", {"site_id": site_id}, maxTimeMS=3000))

    def metadata(self):
        if self._metadata is None or time.monotonic() - self._cached_at > 60:
            summary = list(
                self.sites.aggregate(
                    [{"$group": {"_id": "$language", "count": {"$sum": 1}}}], maxTimeMS=3000
                )
            )
            self._metadata = {
                "records": sum(r["count"] for r in summary),
                "sites": len(self.sites.distinct("site_id", maxTimeMS=3000)),
                "languages": sorted(r["_id"] for r in summary),
                "regions": sorted(self.sites.distinct("regions", maxTimeMS=3000)),
            }
            self._cached_at = time.monotonic()
        return self._metadata

    def image(self, site_id):
        doc = self.sites.find_one(
            {"site_id": site_id, "image_id": {"$exists": True}}, {"image_id": 1}, max_time_ms=3000
        )
        if not doc:
            return None
        try:
            return self.fs.get(doc["image_id"])
        except gridfs.NoFile:
            return None
