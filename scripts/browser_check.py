"""Exercise the running demo with Chromium. Optionally start a local WSGI server for CI."""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run(base, output):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base, wait_until="networkidle")
        expect(page.locator(".site-card")).to_have_count(12)
        expect(page.locator(".site-marker")).to_have_count(12)
        expect(page.locator(".stats>div").nth(2).locator("strong")).to_have_text("5")
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        page.locator("#q").fill("Angkor")
        page.get_by_role("button", name="Explore sites").click()
        expect(page.locator("#results-title")).to_contain_text("Angkor")
        expect(page.get_by_role("heading", name="Angkor", exact=True)).to_be_visible()
        page.locator(".site-card").filter(
            has=page.get_by_role("heading", name="Angkor", exact=True)
        ).click()
        expect(page.locator(".detail-title")).to_have_text("Angkor")
        page.locator("#back-to-results").click()
        expect(page.locator("#q")).to_have_value("Angkor")
        page.goto(base + "/?lat=48.85&lon=2.35&radius=100")
        expect(page.locator(".results-heading")).to_contain_text("Nearest first")
        expect(page.locator(".site-card").first).to_contain_text("km away")
        page.goto(base + "/view/site_0001")
        page.locator("#note").fill("Remember the Viking settlement.")
        page.get_by_role("button", name="Save note", exact=True).click()
        expect(page.locator("#note-status")).to_have_text("Saved on this device.")
        page.locator("#detail-language").select_option("Arabic")
        page.get_by_role("button", name="Apply", exact=True).click()
        expect(page.locator(".detail-title")).to_have_attribute("dir", "auto")
        expect(page.locator(".detail-title")).to_have_attribute("lang", "ar")
        expect(page.locator("#note")).to_have_value("Remember the Viking settlement.")
        page.screenshot(path=str(output / "detail-arabic.png"), full_page=True)
        page.get_by_role("button", name="Delete note", exact=True).click()
        page.reload()
        expect(page.locator("#note")).to_have_value("")
        page.goto(base + "/?q=zzzz-no-results-zzzz")
        expect(page.locator(".empty-state")).to_be_visible()
        page.goto(base + "/?lat=100&lon=0&radius=10")
        expect(page.locator(".error-state")).to_contain_text("Check your search")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(base)
        assert page.evaluate("document.documentElement.scrollWidth") == 390
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        page.goto(base + "/view/site_0001")
        assert page.evaluate("document.documentElement.scrollWidth") == 390
        page.screenshot(path=str(output / "mobile-detail.png"), full_page=True)
        # Blocking map tiles must leave primary search/detail functionality usable.
        page.route("https://*.tile.openstreetmap.org/**", lambda route: route.abort())
        page.goto(base + "/?q=forest")
        expect(page.locator(".site-card").first).to_be_visible()
        assert not errors, errors
        report = {
            "status": "passed",
            "javascript_errors": errors,
            "flows": [
                "map markers",
                "keyword search",
                "search back navigation",
                "nearby search",
                "Arabic translation",
                "private note save/reload/delete",
                "empty results",
                "invalid search",
                "390px responsive layouts",
                "map tile outage",
            ],
        }
        (output / "browser-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:5050")
    parser.add_argument("--output", type=Path, default=ROOT / "work/browser")
    parser.add_argument("--start-server", action="store_true")
    args = parser.parse_args()
    process = None
    log = None
    try:
        if args.start_server:
            log = ROOT / "work/server.log"
            log.parent.mkdir(exist_ok=True)
            log = log.open("w", encoding="utf-8")
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "waitress",
                    "--listen=127.0.0.1:5050",
                    "--call",
                    "app:create_app",
                ],
                cwd=ROOT,
                stdout=log,
                stderr=log,
            )
            for _ in range(50):
                try:
                    urllib.request.urlopen(args.base + "/health/ready", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Demo server did not become ready; inspect work/server.log")
        run(args.base, args.output)
        if (ROOT / "node_modules/axe-core/axe.min.js").exists():
            from accessibility_check import main as accessibility_check

            accessibility_check()
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if log:
            log.close()


if __name__ == "__main__":
    main()
