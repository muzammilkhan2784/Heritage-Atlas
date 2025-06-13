import base64, gridfs
from flask import Flask, render_template, request, session
from pymongo import MongoClient, GEOSPHERE
from bson.objectid import ObjectId
import os

app = Flask(__name__)
app.secret_key = 'any-secret-key-you-want'

client = MongoClient("mongodb://mongoapp:huMONGOu5@localhost:27017/WorldHeritageSites")
db = client.WorldHeritageSites
collection = db.sites_merged
fs = gridfs.GridFS(db)

collection.create_index([("location", GEOSPHERE)])

@app.route("/", methods=["GET", "POST"])
def search():
    results = []
    languages = collection.distinct("language")

    # Initialize default values
    keyword = ""
    lat_str = ""
    lon_str = ""
    radius_str = ""

    if request.method == "POST":
        # Store form values in session
        session["search_query"] = {
            "query": request.form.get("query", "").strip(),
            "lat": request.form.get("lat", "").strip(),
            "lon": request.form.get("lon", "").strip(),
            "radius": request.form.get("radius", "").strip()
        }

    # Load search values from session if they exist
    if "search_query" in session:
        keyword = session["search_query"].get("query", "")
        lat_str = session["search_query"].get("lat", "")
        lon_str = session["search_query"].get("lon", "")
        radius_str = session["search_query"].get("radius", "")

        filters = [{"language": "English"}]  # Always enforce English language filter

        if keyword:
            filters.append({"Name": {"$regex": keyword, "$options": "i"}})

        if all([lat_str, lon_str, radius_str]):
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                radius_km = float(radius_str)
                filters.append({
                    "location": {
                        "$nearSphere": {
                            "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "$maxDistance": radius_km * 1000
                        }
                    }
                })
            except ValueError:
                pass

        if filters:
            results = list(collection.find({"$and": filters}, {"Name": 1, "date_inscribed": 1, "site_id": 1}))

    return render_template(
        "search.html",
        results=results,
        languages=languages,
        keyword=keyword,
        lat=lat_str,
        lon=lon_str,
        radius=radius_str
    )

@app.route("/view/<site_id>", methods=["GET", "POST"])
def view(site_id):
    selected_lang = request.args.get("lang", "English")
    doc = collection.find_one({"site_id": site_id, "language": selected_lang})

    if not doc:
        return render_template("not_found.html", lang=selected_lang)

    if request.method == "POST":
        comment_text = request.form.get("comment", "").strip()
        if comment_text:
            collection.update_many(
                {"site_id": site_id},
                {"$push": {"comments": comment_text}}
            )
            doc = collection.find_one({"site_id": site_id, "language": selected_lang})

    image_base64 = None
    if "image_id" in doc:
        try:
            image_data = fs.get(doc["image_id"]).read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        except:
            pass

    if not image_base64:
        with open("static/default.jpg", "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

    return render_template("detail.html", doc=doc, image=image_base64)

if __name__ == "__main__":
    app.run(debug=True)
