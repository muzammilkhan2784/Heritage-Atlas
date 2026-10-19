"""Automated accessibility regression checks; `npm ci` installs the pinned axe engine."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    reports = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Only the auditing context bypasses CSP so axe can be injected.
        # Application CSP stays enforced in browser_check.py and in the shipped app.
        page = browser.new_page(bypass_csp=True)
        for width, height in [(1440, 1000), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            for path in [
                "/",
                "/view/site_0001",
                "/view/site_0001?lang=Arabic",
                "/?q=zzzz-no-results-zzzz",
            ]:
                page.goto("http://127.0.0.1:5050" + path, wait_until="networkidle")
                page.add_script_tag(path=str(ROOT / "node_modules/axe-core/axe.min.js"))
                report = page.evaluate("""async () => await axe.run(document, {
                    runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}
                })""")
                reports.append(
                    {
                        "path": path,
                        "width": width,
                        "violations": report["violations"],
                        "incomplete_checks": len(report["incomplete"]),
                    }
                )
        browser.close()
    output = ROOT / "work/accessibility.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    for report in reports:
        print(
            report["width"],
            report["path"],
            [(v["id"], len(v["nodes"])) for v in report["violations"]],
        )
    assert not any(report["violations"] for report in reports), (
        "Accessibility violations found; inspect work/accessibility.json"
    )


if __name__ == "__main__":
    main()
