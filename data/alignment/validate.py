"""Check the alignment against a CityOWL network (CWA or OWA), offline.

Usage:
    pip install rdflib owlrl
    python validate.py [--network cwa|owa] INPUT.ttl [INPUT.ttl ...]

Runs materialize.py on the inputs, loads the result with the ontologies
from ../../ontologies (the chosen CityOWL 3.0 network with its document
module, RiC-O 1.1 and PROV-O), computes an OWL 2 RL closure and reports:

  1. Document-ontology restrictions on the data (enforced by CWA only);
  2. that the rules added no doc: triples;
  3. inconsistencies (owl:Nothing members, owl:sameAs between data individuals);
  4. the disjointness of doc:Document declared by CWA core (see
     ontologies/README.md for the namespace fix it needed);
  5. the inferred types of documents, references and city objects.

Exits with status 1 if a check fails.
"""

import argparse
import sys
import tempfile
from pathlib import Path

import owlrl
from rdflib import Graph, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF

import materialize

HERE = Path(__file__).resolve().parent
ONTOLOGIES = HERE.parent.parent / "ontologies"
CITYOWL = "https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/"
DOC = Namespace("https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#")
DATA = "https://raw.githubusercontent.com/VCityTeam/UD-Graph/master/Datasets/GratteCiel_2018_split_v3#"
RICO = "https://www.ica.org/standards/RiC/ontology#"
PROV = "http://www.w3.org/ns/prov#"

NETWORK_FILES = {
    network: [ONTOLOGIES / f"CityOWL/{network.upper()}/3.0" / f"{m}.ttl"
              for m in ("document", "core", "building", "construction", "versioning")]
    for network in ("cwa", "owa")
}
COMMON_FILES = [ONTOLOGIES / "RiC-O/RiC-O_1-1.rdf", ONTOLOGIES / "PROV-O/prov-o.ttl"]

# Document-ontology restrictions on doc:Reference and doc:Tag (CWA module)
EXACTLY_ONE = ["Reference.referringTo", "Reference.coveragePeriod", "Reference.referringDate", "Reference.referenceText"]


def short(term):
    return str(term).split("#")[-1]


def check_restrictions(graph):
    failures = []
    for prop in EXACTLY_ONE:
        cls = DOC[prop.split(".")[0]]
        rows = graph.query(
            f"SELECT ?s WHERE {{ ?s a <{cls}> OPTIONAL {{ ?s <{DOC[prop]}> ?v }} }} GROUP BY ?s HAVING (COUNT(?v) != 1)"
        )
        failures += [f"{short(s)}: {prop} is not exactly one" for (s,) in rows]
    rows = graph.query(
        f"""SELECT ?r WHERE {{ ?r a <{DOC.Reference}>
              FILTER NOT EXISTS {{ ?r <{DOC['Reference.purposeType']}> ?p . ?p a <{DOC.PurposeTypeValue}> }} }}"""
    )
    failures += [f"{short(r)}: no doc:PurposeTypeValue purpose type" for (r,) in rows]
    rows = graph.query(
        f"SELECT ?t WHERE {{ ?t a <{DOC.Tag}> OPTIONAL {{ ?t <{DOC['Tag.text']}> ?x }} }} GROUP BY ?t HAVING (COUNT(?x) != 1)"
    )
    failures += [f"{short(t)}: Tag.text is not exactly one" for (t,) in rows]
    rows = graph.query(f"SELECT ?d ?t WHERE {{ ?d <{DOC['Document.tag']}> ?t FILTER isLiteral(?t) }}")
    failures += [f"{short(d)}: literal tag \"{t}\"" for d, t in rows]
    return failures


def cwa_disjoint_classes():
    """Members of the CWA core AllDisjointClasses axiom that includes doc:Document."""
    core = Graph().parse(ONTOLOGIES / "CityOWL/CWA/3.0/core.ttl")
    for axiom in core.subjects(RDF.type, OWL.AllDisjointClasses):
        members = list(Collection(core, core.value(axiom, OWL.members)))
        if DOC.Document in members:
            return members
    return []


def main(network, inputs):
    with tempfile.TemporaryDirectory() as tmp:
        aligned = Path(tmp) / "aligned.ttl"
        materialize.main(str(aligned), inputs, network)
        graph = Graph().parse(aligned)

    data_only = Graph()
    for path in inputs:
        data_only.parse(path)
    added_doc = [t for t in graph if str(t[1]).startswith(str(DOC)) and t not in data_only]

    print(f"\n== Checks against CityOWL {network.upper()} 3.0")
    failures = []
    restriction_failures = check_restrictions(graph)
    label = "1. Document-ontology restrictions"
    if network == "cwa":
        print(f"{label}: {'OK' if not restriction_failures else 'FAILED'}")
        failures += restriction_failures
    else:
        print(f"{label}: not enforced by OWA ({len(restriction_failures)} deviation(s) from CWA)")
    for line in restriction_failures:
        print(f"   {line}")

    print(f"2. Rules add no doc: triples: {'OK' if not added_doc else f'FAILED ({len(added_doc)})'}")
    failures += [f"rule added {t}" for t in added_doc]

    for path in NETWORK_FILES[network] + COMMON_FILES:
        graph.parse(path)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    nothing = list(graph.subjects(RDF.type, OWL.Nothing))
    same = sorted(
        {tuple(sorted((short(a), short(b)))) for a, b in graph.subject_objects(OWL.sameAs)
         if a != b and str(a).startswith(DATA) and str(b).startswith(DATA)}
    )
    print(f"3. Consistency (OWL 2 RL): {'OK' if not nothing and not same else 'FAILED'}")
    for pair in same:
        print(f"   inferred sameAs {pair}")
    failures += [f"owl:Nothing {short(n)}" for n in nothing] + [f"sameAs {p}" for p in same]

    disjoint = cwa_disjoint_classes()
    clashes = []
    for doc_individual in graph.subjects(RDF.type, DOC.Document):
        for cls in disjoint:
            if cls != DOC.Document and (doc_individual, RDF.type, cls) in graph:
                clashes.append(f"{short(doc_individual)} is also a {short(cls)}")
    print(f"4. CWA disjointness of doc:Document: {'OK' if disjoint and not clashes else 'FAILED'}")
    for line in clashes:
        print(f"   {line}")
    if not disjoint:
        print("   the doc:Document disjointness axiom was not found in CWA core")
    if network == "cwa":
        failures += clashes + ([] if disjoint else ["CWA disjointness axiom missing"])

    afwl = URIRef(f"{CITYOWL}{network.upper()}/3.0/core#AbstractFeatureWithLifespan")
    print("5. Inferred types:")
    for label, query in [
        ("document states", f"?x a <{DOC.Document}>"),
        ("references", f"?x a <{DOC.Reference}>"),
        ("reference targets", f"?r <{DOC['Reference.referringTo']}> ?x"),
    ]:
        individuals = {row[0] for row in graph.query(f"SELECT DISTINCT ?x WHERE {{ {query} }}")}
        types = set()
        for x in individuals:
            types |= {f"rico:{short(t)}" for t in graph.objects(x, RDF.type) if str(t).startswith(RICO) and short(t) != "Thing"}
            types |= {f"prov:{short(t)}" for t in graph.objects(x, RDF.type) if str(t).startswith(PROV)}
        in_network = sum((x, RDF.type, afwl) in graph for x in individuals)
        print(f"   {label} ({len(individuals)}): {in_network} are {network.upper()} core:AbstractFeatureWithLifespan; "
              f"{', '.join(sorted(types)) or 'rico:Thing only'}")

    print(f"\n{'All checks passed' if not failures else f'{len(failures)} check(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("--network", choices=sorted(NETWORK_FILES), default="cwa")
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    sys.exit(main(args.network, args.inputs))
