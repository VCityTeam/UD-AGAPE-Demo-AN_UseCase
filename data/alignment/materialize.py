"""Apply the alignment (RiC-O, PROV-O, Dublin Core) to Turtle files offline.

Usage:
    pip install rdflib
    python materialize.py [--network cwa|owa] OUTPUT.ttl INPUT.ttl [INPUT.ttl ...]

The alignment files in this directory are always loaded. The data uses the
CityOWL CWA vocabulary; with --network owa the CWA-to-OWA bridge is loaded
as well. The rules in rules/ are applied in file-name order and the full
graph is written to OUTPUT.ttl.
"""

import argparse
from pathlib import Path

from rdflib import Graph

HERE = Path(__file__).resolve().parent
ALIGNMENT_FILES = [
    "citygml3-rico.ttl",
    "citygml3-prov.ttl",
    "citygml3-dcterms.ttl",
    "gratteciel-places.ttl",
]
NETWORK_BRIDGES = {
    "cwa": [],
    "owa": ["citygml3-cwa-owa.ttl"],
}


def align(inputs, network="cwa", log=print):
    """Load the alignment files and the inputs, apply the rules, return the graph."""
    graph = Graph()
    files = [HERE / name for name in ALIGNMENT_FILES + NETWORK_BRIDGES[network]]
    for path in files + [Path(p) for p in inputs]:
        graph.parse(path, format="turtle")
    before = len(graph)

    for rule in sorted((HERE / "rules").glob("*.ru")):
        size = len(graph)
        graph.update(rule.read_text(encoding="utf-8"))
        log(f"{rule.name}: +{len(graph) - size} triples")
    return graph, before


def main(output, inputs, network):
    graph, before = align(inputs, network)
    graph.bind("rico", "https://www.ica.org/standards/RiC/ontology#")
    graph.serialize(output, format="turtle")
    print(f"{before} -> {len(graph)} triples written to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("--network", choices=sorted(NETWORK_BRIDGES), default="cwa")
    parser.add_argument("output")
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    main(args.output, args.inputs, args.network)
