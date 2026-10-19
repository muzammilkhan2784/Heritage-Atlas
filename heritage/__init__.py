"""Application factory, HTTP contract, and operational endpoints."""

import logging
import os
import time
import uuid
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, send_file, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from werkzeug.exceptions import HTTPException

from heritage.repository import Repository
from heritage.validation import CATEGORIES, LANGUAGES, InvalidSearch, parse_search


def create_app(config=None):
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__, template_folder=str(root / "templates"), static_folder=str(root / "static")
    )
    app.config.from_mapping(
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27018/heritage"),
        MONGO_DB=os.getenv("MONGO_DB", "heritage"),
        MAX_CONTENT_LENGTH=16384,
    )
    if config:
        app.config.update(config)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=2000,
        socketTimeoutMS=5000,
        appname="heritage-explorer",
    )
    app.extensions["mongo"] = client
    repo = Repository(client[app.config["MONGO_DB"]])
    app.extensions["repository"] = repo

    @app.before_request
    def start_request():
        g.started = time.monotonic()
        g.request_id = uuid.uuid4().hex

    @app.after_request
    def finish_request(response):
        response.headers.update(
            {
                "X-Request-ID": g.request_id,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https://*.tile.openstreetmap.org; "
                    "connect-src 'self'; object-src 'none'; base-uri 'self'; "
                    "frame-ancestors 'none'; form-action 'self'"
                ),
            }
        )
        app.logger.info(
            "request id=%s method=%s path=%s status=%s duration_ms=%.1f",
            g.request_id,
            request.method,
            request.path,
            response.status_code,
            (time.monotonic() - g.started) * 1000,
        )
        return response

    @app.context_processor
    def context():
        return {"language_codes": LANGUAGES, "categories": CATEGORIES}

    @app.get("/")
    def search():
        try:
            filters = parse_search(request.args)
        except InvalidSearch as exc:
            return render_template("error.html", title="Check your search", message=str(exc)), 400
        result = repo.search(filters)

        def page_url(page):
            return url_for("search", **(filters.params() | {"page": page}))

        return render_template(
            "search.html",
            filters=filters,
            result=result,
            metadata=repo.metadata(),
            page_url=page_url,
            available_languages=repo.languages_for([doc["site_id"] for doc in result["items"]]),
        )

    @app.get("/view/<site_id>")
    def view(site_id):
        language = request.args.get("lang", "English")
        if language not in LANGUAGES:
            abort(400, "Choose a supported language.")
        doc = repo.detail(site_id, language)
        if doc is None:
            abort(404, "This site is not available in the selected language.")
        return render_template("detail.html", doc=doc, languages=repo.languages(site_id))

    @app.get("/api/sites")
    def api_sites():
        try:
            filters = parse_search(request.args)
        except InvalidSearch as exc:
            return jsonify(
                error={"code": "invalid_search", "message": str(exc), "request_id": g.request_id}
            ), 400
        return jsonify(repo.search(filters))

    @app.get("/api/sites/<site_id>")
    def api_site(site_id):
        language = request.args.get("language", "English")
        if language not in LANGUAGES:
            abort(400, "Choose a supported language.")
        doc = repo.detail(site_id, language)
        if doc is None:
            abort(404, "Site or translation not found.")
        return jsonify(doc)

    @app.get("/api/metadata")
    def api_metadata():
        return jsonify(repo.metadata())

    @app.get("/media/<site_id>")
    def image(site_id):
        size = request.args.get("size", "full")
        if size not in {"full", "thumb"}:
            abort(400, "Image size must be full or thumb.")
        image = repo.image(site_id, thumbnail=size == "thumb")
        if image is None:
            return redirect(url_for("static", filename="images/landscape.svg"))
        # Only trusted raster images are served; never render imported HTML/SVG.
        mime = (image.metadata or {}).get("content_type")
        if mime not in {"image/jpeg", "image/png", "image/webp"} or image.length > 10_000_000:
            image.close()
            return redirect(url_for("static", filename="images/landscape.svg"))
        return send_file(
            image,
            mimetype=mime,
            download_name=f"{site_id}.image",
            etag=str(image._id),
            max_age=86400,
            conditional=True,
        )

    @app.get("/health/live")
    def live():
        return jsonify(status="ok")

    @app.get("/health/ready")
    def ready():
        client.admin.command("ping")
        if repo.sites.estimated_document_count() == 0:
            return jsonify(status="not_ready", reason="dataset_not_loaded"), 503
        indexes = repo.sites.index_information()
        if not any(("location", "2dsphere") in index["key"] for index in indexes.values()):
            return jsonify(status="not_ready", reason="indexes_not_created"), 503
        return jsonify(status="ready")

    @app.errorhandler(PyMongoError)
    def unavailable(exc):
        app.logger.error("database_error id=%s type=%s", g.request_id, type(exc).__name__)
        if request.path.startswith(("/api/", "/health/")):
            return jsonify(
                error={
                    "code": "service_unavailable",
                    "message": "Database temporarily unavailable.",
                    "request_id": g.request_id,
                }
            ), 503
        return render_template(
            "error.html",
            title="We’ll be back shortly",
            message="The heritage archive is temporarily unavailable. Please try again shortly.",
        ), 503

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if request.path.startswith("/api/"):
            return jsonify(
                error={
                    "code": exc.name.lower().replace(" ", "_"),
                    "message": exc.description,
                    "request_id": g.request_id,
                }
            ), exc.code
        return render_template("error.html", title=exc.name, message=exc.description), exc.code

    from heritage.ingestion import register_commands

    register_commands(app)
    return app
