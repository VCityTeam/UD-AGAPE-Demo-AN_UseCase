"""Build the 3D viewer's scene from the RDF data.

Usage:
    pip install rdflib
    python build_scene.py

Aligns ../gratteciel/gratteciel-documents.ttl and gratteciel-geometry.ttl
with ../alignment (RiC-O, PROV-O), then writes scene.js with:
  - each building's LoD2 roof and wall polygons, in metres relative to the
    centre of the documented buildings (EPSG:3946 x/y, source heights);
  - each RiC record with its instantiations (document states) and its
    qualified references (rico:Relation): target, purpose, depicted period,
    assertion date, and the buildings each reference reaches, directly or
    through the place its target is located at.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "alignment"))
import materialize  # noqa: E402

DATA = HERE.parent / "gratteciel"
INPUTS = [DATA / "gratteciel-documents.ttl", DATA / "gratteciel-geometry.ttl"]
PREFIXES = """
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX doc:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX bldg: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/building#>
PREFIX con:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/construction#>
PREFIX core: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/core#>
PREFIX geo:  <http://www.opengis.net/ont/geosparql#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX align: <https://raw.githubusercontent.com/VCityTeam/UD-AGAPE-Demo-AN_UseCase/master/data/alignment/citygml3-rico.ttl#>
"""


def short(term):
    return str(term).split("#")[-1]


def query(graph, body):
    return list(graph.query(PREFIXES + body))


def years(normalized):
    """'1936', '1932-01', '1930/1931', '2023-12-28' -> (first year, last year)."""
    parts = [int(p[:4]) for p in str(normalized).split("/")]
    return parts[0], parts[-1]


def display_date(value):
    """xsd:dateTime -> '1936' (1 January, midnight: year only), '2020-03' (first of month), or the full date.

    The data stores dates known only to the year or month as the first day of that period.
    """
    if not value:
        return ""
    text = str(value)
    date, time = text[:10], text[11:19]
    if time in ("", "00:00:00") and date.endswith("-01-01"):
        return date[:4]
    if time in ("", "00:00:00") and date.endswith("-01"):
        return date[:7]
    return date


def commons_thumbnail(page):
    """Thumbnail URL for a Wikimedia Commons file page, else None."""
    match = re.match(r"https://commons\.wikimedia\.org/wiki/File:(.+)$", str(page or ""))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{match.group(1)}?width=480" if match else None


def buildings(graph):
    """Buildings with their LoD2 surfaces: [{id, label, surfaces: [{id, type, label, rings}]}]."""
    rows = query(graph, """
        SELECT ?building ?label ?surface ?type ?surfaceLabel ?gml WHERE {
          ?building a bldg:Building ; core:AbstractSpace.boundary ?surface .
          OPTIONAL { ?building rdfs:label ?name FILTER(lang(?name) = "fr") }
          OPTIONAL { ?building skos:prefLabel ?id }
          BIND(COALESCE(?name, ?id) AS ?label)
          OPTIONAL { ?surface skos:prefLabel ?surfaceLabel FILTER(lang(?surfaceLabel) = "en") }
          ?surface a ?type ; core:AbstractThematicSurface.lod2MultiSurface/geo:asGML ?gml .
          VALUES ?type { con:RoofSurface con:WallSurface }
        }""")
    result = {}
    for building, label, surface, surface_type, surface_label, gml in rows:
        entry = result.setdefault(short(building), {"id": short(building), "label": str(label or short(building)),
                                                    "surfaces": {}})
        kind = "roof" if short(surface_type) == "RoofSurface" else "wall"
        item = entry["surfaces"].setdefault(short(surface), {
            "id": short(surface), "type": kind, "label": str(surface_label or f"{kind} surface"), "rings": []})
        for pos_list in re.findall(r"<gml:posList[^>]*>([^<]+)</gml:posList>", str(gml)):
            item["rings"].append([float(v) for v in pos_list.split()])
    for entry in result.values():
        entry["surfaces"] = sorted(entry["surfaces"].values(), key=lambda s: (s["type"], s["id"]))
    return result


def rings_of(building):
    return [ring for surface in building["surfaces"] for ring in surface["rings"]]


def localise(result, documented):
    """Shift coordinates to metres around the documented buildings, rounded to centimetres."""
    points = [ring[i:i + 3] for b in documented for ring in rings_of(result[b]) for i in range(0, len(ring), 3)]
    origin = [sum(p[k] for p in points) / len(points) for k in range(2)]
    ground = min(ring[i] for b in result.values() for ring in rings_of(b) for i in range(2, len(ring), 3))
    shift = (origin[0], origin[1], ground)
    for building in result.values():
        for surface in building["surfaces"]:
            surface["rings"] = [[round(v - shift[i % 3], 2) for i, v in enumerate(ring)] for ring in surface["rings"]]
    return {"x": round(shift[0], 3), "y": round(shift[1], 3), "z": round(shift[2], 3), "crs": "EPSG:3946"}


def convex_hull(points):
    """2D convex hull (monotone chain), counter-clockwise."""
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def half(sequence):
        hull = []
        for p in sequence:
            while len(hull) >= 2 and ((hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1])
                                      - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])) <= 0:
                hull.pop()
            hull.append(p)
        return hull[:-1]
    return half(points) + half(reversed(points))


def places(graph, scene_buildings):
    """Places with the buildings located in them and a ground outline (convex hull of their footprints)."""
    result = []
    for place_iri, name in query(graph, """
        SELECT ?p ?name WHERE { ?p a rico:Place ; rico:hasOrHadPlaceName/rico:textualValue ?name }"""):
        located = sorted(short(b) for (b,) in query(graph, f"""
            SELECT ?b WHERE {{ ?b a bldg:Building ; rico:hasOrHadLocation <{place_iri}> }}""")
            if short(b) in scene_buildings)
        if not located:
            continue
        footprint = [(ring[i], ring[i + 1]) for b in located for ring in rings_of(scene_buildings[b])
                     for i in range(0, len(ring), 3)]
        result.append({"id": short(place_iri), "name": str(name), "buildings": located,
                       "outline": [c for p in convex_hull(footprint) for c in p]})
    return result


def derivation_order(states):
    """Order states along their derivation chain, oldest first."""
    ordered = [s for s in states if not s["derivedFrom"]]
    while len(ordered) < len(states):
        ordered += [s for s in states if s["derivedFrom"] == ordered[-1]["id"]]
    return ordered


def records(graph):
    result = {}
    for record, title in query(graph, "SELECT ?r ?t WHERE { ?r a rico:Record ; rico:title ?t }"):
        result[short(record)] = {"id": short(record), "title": str(title), "states": [], "references": []}

    for record, state, title, uri, page, created, derived, creator, licence in query(graph, """
        SELECT ?record ?state ?title ?uri ?page ?created ?derived ?creator ?licence WHERE {
          ?record rico:hasOrHadInstantiation ?state .
          OPTIONAL { ?state rico:title ?title }
          OPTIONAL { ?state doc:Document.uri ?uri }
          OPTIONAL { ?state rdfs:seeAlso ?page }
          OPTIONAL { ?state rico:creationDate ?created }
          OPTIONAL { ?state rico:isOrWasDerivedFromInstantiation ?derived }
          OPTIONAL { ?state dct:creator ?creator }
          OPTIONAL { ?state dct:license ?licence }
        }"""):
        result[short(record)]["states"].append({
            "id": short(state), "title": str(title or ""), "uri": str(uri or ""), "page": str(page or ""),
            "created": display_date(created), "derivedFrom": short(derived) if derived else None,
            "creator": str(creator or ""), "licence": str(licence or ""), "thumbnail": commons_thumbnail(page)})

    for record, relation, state, target, target_label, purpose, depicted, asserted, text, certainty in query(graph, """
        SELECT ?record ?relation ?state ?target ?targetLabel ?purpose ?depicted ?asserted ?text ?certainty WHERE {
          ?record rico:hasOrHadInstantiation ?state .
          ?state rico:thingIsSourceOfRelation ?relation .
          ?relation rico:relationHasTarget ?target ; rico:generalDescription ?text .
          OPTIONAL { ?target skos:prefLabel ?targetLabel FILTER(lang(?targetLabel) IN ("", "en")) }
          OPTIONAL { ?relation rico:hasOrHadType/skos:prefLabel ?purpose FILTER(lang(?purpose) = "en") }
          OPTIONAL { ?relation rico:relationCertainty ?certainty }
          ?relation rico:relationHasDate ?c, ?a .
          ?c rico:hasDateType align:dateType_coveragePeriod ; rico:normalizedDateValue ?depicted .
          ?a rico:hasDateType align:dateType_assertion ; rico:normalizedDateValue ?asserted .
        }"""):
        # scale of the reference: the building itself, one of its surfaces, or a place
        reached_place = []
        bounding = [short(b) for (b,) in query(graph, f"SELECT ?b WHERE {{ ?b a bldg:Building ; core:AbstractSpace.boundary <{target}> }}")]
        if query(graph, f"ASK {{ <{target}> a bldg:Building }}")[0]:
            scale, reached = "building", [short(target)]
        elif bounding:
            scale, reached = "surface", bounding
        else:
            scale = "place"
            reached_place = [short(p) for (p,) in query(graph, f"SELECT ?p WHERE {{ <{target}> rico:hasOrHadLocation ?p }}")]
            reached = [short(b) for (b,) in query(graph, f"""
                SELECT DISTINCT ?b WHERE {{
                  <{target}> rico:hasOrHadLocation ?p . ?b a bldg:Building ; rico:hasOrHadLocation ?p .
                }}""")]
        first, last = years(depicted)
        result[short(record)]["references"].append({
            "id": short(relation), "state": short(state), "target": short(target),
            "targetLabel": str(target_label or short(target)), "purpose": str(purpose or ""),
            "depicted": str(depicted), "from": first, "to": last, "asserted": str(asserted)[:10],
            "text": str(text), "buildings": sorted(reached), "scale": scale, "direct": scale != "place",
            "place": reached_place[0] if scale == "place" and reached_place else None,
            "certainty": str(certainty or "")})

    for entry in result.values():
        entry["states"] = derivation_order(entry["states"])
        entry["references"].sort(key=lambda r: (r["asserted"], r["target"]))
    return sorted(result.values(), key=lambda r: (min(ref["from"] for ref in r["references"]), r["id"]))


def place(graph):
    rows = query(graph, """
        SELECT ?name ?lat ?lon WHERE {
          ?p a rico:Place ; rico:hasOrHadPlaceName/rico:textualValue ?name ;
             rico:hasOrHadPhysicalLocation/rico:hasOrHadCoordinates ?c .
          ?c rico:latitude ?lat ; rico:longitude ?lon .
        }""")
    name, lat, lon = rows[0]
    return {"name": str(name), "lat": float(lat), "lon": float(lon)}


def main():
    graph, _ = materialize.align([str(p) for p in INPUTS], log=lambda *_: None)
    scene_buildings = buildings(graph)
    scene_records = records(graph)
    documented = sorted({b for r in scene_records for ref in r["references"] for b in ref["buildings"]})
    origin = localise(scene_buildings, documented)
    scene = {"origin": origin, "place": place(graph), "places": places(graph, scene_buildings),
             "buildings": sorted(scene_buildings.values(), key=lambda b: b["id"]), "records": scene_records}
    output = HERE / "scene.js"
    output.write_text("// Generated by build_scene.py from the RDF data; do not edit.\nwindow.SCENE = "
                      + json.dumps(scene, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"{len(scene['buildings'])} buildings ({len(documented)} documented), "
          f"{len(scene_records)} records, {sum(len(r['references']) for r in scene_records)} references "
          f"-> {output.name} ({output.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
