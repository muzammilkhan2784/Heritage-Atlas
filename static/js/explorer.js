"use strict";
(() => {
  const form = document.getElementById("search-form");
  const status = document.getElementById("location-status");
  const setLocation = (lat, lon) => {
    if (!form) return;
    document.getElementById("lat").value = Number(lat).toFixed(5);
    document.getElementById("lon").value = Number(lon).toFixed(5);
    document.getElementById("radius").value ||= "100";
    document.querySelector(".nearby").open = true;
    status.textContent = "Location set. Choose Explore sites to search nearby.";
  };
  if (form) {
    try {
      sessionStorage.setItem(
        "heritage:lastSearch",
        location.pathname + location.search + "#explore",
      );
    } catch {
      /* Storage can be disabled. */
    }
    // GET searches never send blank coordinate or filter values.
    form.addEventListener("submit", () => {
      for (const control of form.querySelectorAll("input, select")) {
        if (control.value === "") control.disabled = true;
      }
    });
    document.getElementById("clear-location").addEventListener("click", () => {
      for (const id of ["lat", "lon", "radius"])
        document.getElementById(id).value = "";
      status.textContent =
        "Location cleared. Choose Explore sites to update results.";
    });
    document.getElementById("locate").addEventListener("click", () => {
      if (!navigator.geolocation) {
        status.textContent =
          "Geolocation is unavailable. Enter coordinates instead.";
        return;
      }
      status.textContent = "Waiting for location permission…";
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => setLocation(coords.latitude, coords.longitude),
        () => {
          status.textContent =
            "Location could not be retrieved. Enter coordinates or select a map point.";
        },
        { timeout: 10000, maximumAge: 60000 },
      );
    });
  }
  const back = document.getElementById("back-to-results");
  if (back) {
    try {
      const saved = sessionStorage.getItem("heritage:lastSearch");
      if (saved) {
        const target = new URL(saved, location.origin);
        if (target.origin === location.origin && target.pathname === "/")
          back.href = target.href;
      }
    } catch {
      /* Use the server-rendered fallback link. */
    }
  }
  const note = document.getElementById("note");
  if (note) {
    const key = "heritage:note:" + note.dataset.siteId;
    const feedback = document.getElementById("note-status");
    try {
      note.value = localStorage.getItem(key) || "";
    } catch {
      feedback.textContent = "Browser storage is unavailable.";
    }
    document.getElementById("save-note").addEventListener("click", () => {
      try {
        localStorage.setItem(key, note.value.trim());
        feedback.textContent = "Saved on this device.";
      } catch {
        feedback.textContent =
          "Could not save. Browser storage may be disabled or full.";
      }
    });
    document.getElementById("delete-note").addEventListener("click", () => {
      try {
        localStorage.removeItem(key);
        note.value = "";
        feedback.textContent = "Note deleted.";
      } catch {
        feedback.textContent = "Could not delete the saved note.";
      }
    });
  }
  const mapElement = document.getElementById("map");
  const mapData = document.getElementById("map-data");
  if (mapElement && mapData && typeof L !== "undefined") {
    const sites = JSON.parse(mapData.textContent);
    const map = L.map(mapElement, { scrollWheelZoom: false }).setView(
      [24, 15],
      2,
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    const bounds = [];
    for (const site of sites) {
      const [lon, lat] = site.location.coordinates;
      const popup = document.createElement("div");
      const link = document.createElement("a");
      link.href =
        "/view/" +
        encodeURIComponent(site.site_id) +
        "?lang=" +
        encodeURIComponent(site.language);
      link.textContent = site.name;
      popup.append(
        link,
        document.createElement("br"),
        document.createTextNode(site.country + " · " + site.year),
      );
      const icon = L.divIcon({ className: "site-marker", iconSize: [13, 13] });
      const marker = L.marker([lat, lon], { icon, title: site.name })
        .addTo(map)
        .bindPopup(popup);
      marker.getElement().setAttribute("aria-label", site.name);
      bounds.push([lat, lon]);
    }
    if (bounds.length)
      map.fitBounds(bounds, {
        padding: [30, 30],
        maxZoom: bounds.length === 1 ? 8 : 6,
      });
    if (form) {
      let selected;
      map.on("click", ({ latlng }) => {
        const longitude = ((((latlng.lng + 180) % 360) + 360) % 360) - 180;
        setLocation(Math.max(-90, Math.min(90, latlng.lat)), longitude);
        if (selected) map.removeLayer(selected);
        selected = L.marker([latlng.lat, longitude], {
          icon: L.divIcon({
            className: "site-marker selected-marker",
            iconSize: [16, 16],
          }),
        }).addTo(map);
      });
    }
  }
})();
