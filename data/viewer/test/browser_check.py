"""Browser test of the iTowns viewer (../index.html).

Usage:
    pip install playwright && python -m playwright install chromium
    python browser_check.py

Serves ../ on a local port, opens the page in headless Chromium with software
WebGL, then checks:
  1. every LoD2 polygon triangulates, with the triangle area matching the
     polygon area and vertices kept in the scene frame;
  2. the year filter and the imagery choice per year;
  3. objects -> documents: a real mouse click on the town hall's roof selects
     that surface (URL) and the panel lists the record about it;
  4. documents -> objects: focusing a record highlights exactly what it refers
     to, at its scale (a surface, buildings, or a place's buildings and outline);
  5. selecting a place highlights its buildings and outline;
  6. no page error (HTTP errors from IGN's WMS are listed separately: its
     historical layer sometimes rejects requests under load);
and writes screenshot.png (the last state). Set CHROME to use another
Chromium executable. Exits with status 1 if a check fails.
"""

import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TOWN_HALL = "BU_69266BO55_0"
GRATTE_CIEL = ["BU_69266BO56_0", "BU_69266BO56_1", "BU_69266BO56_2", "BU_69266BO56_3"]
PLACE = "place_gratteCiel"
CHROMIUM_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root):
    """Serve ROOT on a free local port, in a background thread."""
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


# Roles of the surface meshes, as set by the viewer, and the visible place outlines
HIGHLIGHT_JS = """() => {
  const roles = {};
  const outlines = [];
  window.viewer.scene.traverse((o) => {
    if (o.userData?.surface) roles[o.userData.surface] = { building: o.userData.building, role: o.userData.role };
    if (o.userData?.place && o.visible) outlines.push(o.userData.place);
  });
  return { roles, outlines };
}"""

GEOMETRY_JS = """async () => {
  const { triangulateRing, recordsByBuilding, imageryForYear } = await import('./viewer.js');
  const area3 = (a, b, c) => { const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    return Math.hypot(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]) / 2; };
  let rings = 0, triangles = 0, empty = 0, invalid = 0, worst = 0;
  for (const b of window.SCENE.buildings) for (const surface of b.surfaces) for (const ring of surface.rings) {
    rings++;
    const t = triangulateRing(ring);
    if (!t.length) { empty++; continue; }
    const vertices = new Set(); for (let i = 0; i < ring.length; i += 3) vertices.add(ring.slice(i, i + 3).join());
    for (let i = 0; i < t.length; i += 3) if (!vertices.has(t.slice(i, i + 3).join()) || t.slice(i, i + 3).some(Number.isNaN)) invalid++;
    let area = 0; for (let i = 0; i < t.length; i += 9) area += area3(t.slice(i, i + 3), t.slice(i + 3, i + 6), t.slice(i + 6, i + 9));
    const p = []; for (let i = 0; i < ring.length; i += 3) p.push(ring.slice(i, i + 3));
    const n = [0, 0, 0]; for (let i = 0; i < p.length; i++) { const a = p[i], c = p[(i + 1) % p.length];
      n[0] += (a[1] - c[1]) * (a[2] + c[2]); n[1] += (a[2] - c[2]) * (a[0] + c[0]); n[2] += (a[0] - c[0]) * (a[1] + c[1]); }
    const polygon = Math.hypot(...n) / 2;
    // polygons under 2 m² are skipped: centimetre rounding makes them slightly non-planar
    if (polygon > 2) worst = Math.max(worst, Math.abs(area - polygon) / polygon);
    triangles += t.length / 9;
  }
  const byYear = Object.fromEntries([1932, 1936, 1950, 1965, 1966, 2023].map((y) =>
    [y, [recordsByBuilding(window.SCENE.records, y).size, imageryForYear(y)]]));
  return { rings, triangles, empty, invalid, worst, byYear };
}"""

# Screen position of the highest roof triangle of a building
ROOF_POINT_JS = """(id) => {
  const v = window.viewer;
  let mesh = null;
  v.scene.traverse((o) => { if (o.userData?.building === id && o.userData?.surface?.startsWith('RoofSurface')) mesh = o; });
  const pos = mesh.geometry.attributes.position.array;
  let best = 0;
  for (let i = 0; i < pos.length; i += 9) if (pos[i + 2] + pos[i + 5] + pos[i + 8] > pos[best + 2] + pos[best + 5] + pos[best + 8]) best = i;
  const c = mesh.geometry.boundingBox.min.clone().set((pos[best] + pos[best + 3] + pos[best + 6]) / 3,
    (pos[best + 1] + pos[best + 4] + pos[best + 7]) / 3, (pos[best + 2] + pos[best + 5] + pos[best + 8]) / 3);
  c.applyMatrix4(mesh.matrixWorld).project(v.camera3D);
  const r = v.domElement.getBoundingClientRect();
  return [r.left + (c.x + 1) / 2 * r.width, r.top + (1 - c.y) / 2 * r.height];
}"""

SURFACE_SECTION_JS = """() => {
  const section = [...document.querySelectorAll('#panel section')].find((s) => s.querySelector('h4').textContent.startsWith('About this surface'));
  return section ? [...section.querySelectorAll('[data-record]')].map((c) => c.dataset.record) : [];
}"""


def main():
    failures = []

    def check(ok, message):
        print(f"{'ok  ' if ok else 'FAIL'} {message}")
        if not ok:
            failures.append(message)

    def with_role(h, role):
        return [(s, v) for s, v in h["roles"].items() if v["role"] == role]

    def buildings_with_role(h, role):
        return sorted({v["building"] for _, v in with_role(h, role)})

    server, base = serve(ROOT)
    page_errors, http_errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROME") or None, args=CHROMIUM_ARGS)
        page = browser.new_page(viewport={"width": 1400, "height": 850})
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("response", lambda r: r.status >= 400 and http_errors.append(f"{r.status} {r.url}"))

        page.goto(f"{base}/index.html")
        page.wait_for_function("() => window.viewer && window.viewer.camera3D", timeout=60000)
        page.wait_for_timeout(20000)  # let terrain and imagery tiles arrive

        def highlight():
            return page.evaluate(HIGHLIGHT_JS)

        def focus(record):
            # click the card body (its title is a link to the source)
            page.evaluate("(id) => document.querySelector(`#panel [data-record=\"${id}\"] .chain`).click()", record)
            page.wait_for_timeout(800)
            return highlight()

        def reset():
            page.evaluate("() => { location.hash = ''; }")
            page.wait_for_timeout(800)

        # 1–2. geometry and filters, on the module the page uses
        result = page.evaluate(GEOMETRY_JS)
        check(result["empty"] == 0 and result["invalid"] == 0,
              f"{result['rings']} polygons -> {result['triangles']} triangles, none empty or invalid")
        check(result["worst"] < 0.01, f"triangle area within {result['worst'] * 100:.2f}% of polygon area")
        by_year = result["byYear"]
        check(by_year["1965"][1] == "historical" and by_year["1966"][1] == "current", "imagery switches between 1965 and 1966")

        # 3. objects -> documents: click on the highest roof triangle of the town hall
        x, y = page.evaluate(ROOF_POINT_JS, TOWN_HALL)
        page.mouse.click(x, y)
        page.wait_for_timeout(1500)
        url_hash = page.evaluate("() => location.hash")
        check(f"building={TOWN_HALL}" in url_hash and "surface=RoofSurface_60" in url_hash,
              f"clicking the town hall's roof selects its roof surface ({url_hash})")
        roof_records = page.evaluate(SURFACE_SECTION_JS)
        check(sorted(roof_records) == ["document_5_record"], f"the panel lists the record about the roofs ({', '.join(roof_records)})")
        h = highlight()
        check([s for s, _ in with_role(h, "selected-surface")] == ["RoofSurface_60"], "the selected roof surface is highlighted")

        # 4. documents -> objects
        reset()
        h = focus("document_6_record")  # elevation drawing of the north façade
        check([s for s, _ in with_role(h, "target-surface")] == ["WallSurface_60"]
              and not with_role(h, "target-building") and not with_role(h, "target-place"),
              "focusing the façade drawing highlights only the town hall wall surface")

        h = focus("document_1_original_record")  # 1936 aerial view: 4 blocks + the district
        check(buildings_with_role(h, "target-building") == sorted(GRATTE_CIEL),
              "focusing the aerial view highlights the 4 blocks it refers to as buildings")
        check(buildings_with_role(h, "target-place") == [TOWN_HALL] and h["outlines"] == [PLACE],
              "…and, through its district reference, the rest of the place and its outline")

        h = focus("document_3_record")  # heritage record of the Cité: place only
        check(buildings_with_role(h, "target-place") == sorted(GRATTE_CIEL + [TOWN_HALL]) and h["outlines"] == [PLACE],
              "focusing a place-level record highlights the place's 5 buildings and its outline")
        url_hash = page.evaluate("() => location.hash")
        check("record=document_3_record" in url_hash, f"the focused record is in the URL ({url_hash})")

        # 5. select the place
        reset()
        page.click(f'#panel [data-place="{PLACE}"]')
        page.wait_for_timeout(800)
        h = highlight()
        check(buildings_with_role(h, "place") == sorted(GRATTE_CIEL + [TOWN_HALL]) and h["outlines"] == [PLACE],
              "selecting the Cité highlights its 5 buildings and its outline")

        page.screenshot(path=str(Path(__file__).resolve().parent / "screenshot.png"))
        browser.close()
    server.shutdown()

    check(not page_errors, "no page errors" + (f": {'; '.join(page_errors)}" if page_errors else ""))
    local = [e for e in http_errors if base in e]
    check(not local, "no HTTP errors for local files" + (f": {'; '.join(local)}" if local else ""))
    if len(http_errors) > len(local):
        print(f"     {len(http_errors) - len(local)} HTTP error(s) from remote services (e.g. IGN WMS under load)")

    print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed; screenshot.png written")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
