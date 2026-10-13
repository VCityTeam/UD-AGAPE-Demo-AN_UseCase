"""Regenerate the README screenshots of the viewer from shareable views.

Usage:
    pip install playwright && python -m playwright install chromium
    python screenshots.py            # writes ../screenshot*.png

Each view is a URL hash of the viewer (see ../README.md). Set CHROME to use
another Chromium executable.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from browser_check import CHROMIUM_ARGS, ROOT, serve

VIEWS = {
    "screenshot.png": "building=BU_69266BO56_3&year=1936",
    "screenshot-townhall.png": "building=BU_69266BO55_0&surface=WallSurface_60&year=1991",
    "screenshot-record-surface.png": "record=document_6_record",
    "screenshot-record-place.png": "record=document_1_original_record&year=1936",
    "screenshot-place.png": "place=place_gratteCiel",
}


def main():
    server, base = serve(ROOT)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROME") or None, args=CHROMIUM_ARGS)
        for file, view in VIEWS.items():
            page = browser.new_page(viewport={"width": 1400, "height": 850})
            page.goto(f"{base}/index.html#{view}")
            page.wait_for_function("() => window.viewer && window.viewer.camera3D", timeout=60000)
            page.wait_for_timeout(25000)  # terrain and imagery tiles
            page.evaluate("() => document.querySelector('#panel .record.focused')?.scrollIntoView({ block: 'start' })")
            page.screenshot(path=str(ROOT / file))
            print(f"{file}  <-  #{view}")
            page.close()
        browser.close()
    server.shutdown()


if __name__ == "__main__":
    main()
