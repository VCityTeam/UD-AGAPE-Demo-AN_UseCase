# Ontologies

Ontologies used to align urban documentation (CityGML 3.0 and the Document ontology) with archival description (RiC-O) for the AGAPE Poject, including Archives Nationales use case.

## Contents

| Path | Source | Modified |
|---|---|---|
| [`CityOWL/CWA/3.0/`](CityOWL/CWA/3.0/) | [CityOWL CWA 3.0](https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/): CityGML 3.0 with a **closed-world** reading (restrictions on cardinality and value types, disjointness); the recommended network | yes, see below |
| [`CityOWL/OWA/3.0/`](CityOWL/OWA/3.0/) | [CityOWL OWA 3.0](https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/OWA/3.0/): the same model with an **open-world** reading (domains and ranges only) | yes, see below |
| [`Document/3.0/document.ttl`](Document/3.0/document.ttl) | [Document 3.0](https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document.ttl): an earlier Document ontology built on the older `CityGML/3.0` network, kept for reference. It uses the same `doc:` namespace as the CityOWL document modules; do not load it together with them. | no |
| [`RiC-O/RiC-O_1-1.rdf`](RiC-O/RiC-O_1-1.rdf) | [ICA-EGAD/RiC-O](https://github.com/ICA-EGAD/RiC-O/tree/master/ontology/current-version), Records in Contexts ontology 1.1 | no |
| [`PROV-O/prov-o.ttl`](PROV-O/prov-o.ttl) | [W3C PROV-O](https://www.w3.org/ns/prov-o) | no |

Both CityRDF networks use the same Document namespace (`.../Document/3.0/document#`) but different CityGML namespaces (`.../CityOWL/CWA/3.0/...#` and `.../CityOWL/OWA/3.0/...#`). Load one network at a time.

The CWA `document` module is the Document ontology described in *From Versioned Cities to Versioned Documents: Extending CityRDF for Modelling Urban Documentation over Time* (3DGeoInfo 2026). It separates a document from the qualified `doc:Reference` that links it to an urban feature, with a coverage period, an assertion date and a purpose.

## Extensions

Both networks now offer the same Document vocabulary. Before, each lacked part of it.

| Module | Added | Why |
|---|---|---|
| `CWA/3.0/document.ttl` | `doc:DocumentableVersion`, `doc:DocumentableVersionTransition` | Document versioning: a document evolves through successive states (scan, restoration, annotation). The OWA module and the earlier [Document 3.0](Document/3.0/document.ttl) ontology declare these classes; the CWA module did not. They have no properties yet. |
| `OWA/3.0/document.ttl` | `doc:Document.referringTo` (domain `doc:Document`, range `doc:Reference`) and `doc:Reference.referringTo` (domain `doc:Reference`, range `core:AbstractFeatureWithLifespan`) | These two properties connect a document to an urban feature through a reference, the core of the Document model. The CWA module declares them; the OWA module did not. They are added in OWA style, with a domain and range but no cardinality restriction. |
| `OWA/3.0/document.ttl` | `doc:PurposeTypeValue ⊑ skos:Concept` | Used as the range of `doc:Reference.purposeType` but not declared; declared as in the CWA module |

| | CWA | OWA |
|---|---|---|
| `doc:Document`, `doc:Reference`, `doc:Tag` and their properties | yes | yes |
| `doc:Document.referringTo`, `doc:Reference.referringTo` | yes, exactly one target per reference | yes, domain and range only (**added**) |
| `doc:PurposeTypeValue ⊑ skos:Concept` | yes | yes (**added**) |
| Restrictions on references and tags | yes | none (open world) |
| `doc:DocumentableVersion`, `doc:DocumentableVersionTransition` | yes (**added**) | yes |

## Corrections

Errors in the published files, each corrected with the smallest possible change.

| Module | Problem | Correction |
|---|---|---|
| `CWA/3.0/core.ttl` | The `owl:AllDisjointClasses` axiom lists `doc:Document` and `wksp:Scenario`, `wksp:Space`, `wksp:Workspace`, but the file bound `doc:` to `.../CityOWL/CWA/3.0/document#` and `wksp:` to `.../CityOWL/CWA/3.0/workspace#`. Neither namespace defines anything, so the axiom never applied to the real classes. | Prefixes bound to the namespaces where the classes are defined: `.../Document/3.0/document#` and `.../Workspace/3.0/workspace#` |
| `CWA/3.0/core.ttl` | Five `core:CityModel.cityModelMember_*` properties were declared sub-properties of `core:cityModelMember`, which does not exist | Parent changed to `core:CityModel.cityModelMember` |
| `CWA/3.0/transportation.ttl` | `tran:SquareUsageValue` is used as a range and in a restriction but was never declared, unlike `tran:SquareClassValue` and `tran:SquareFunctionValue` | Declared like them, as a subclass of `skos:Concept` |
| `CWA/3.0/transactiontypevalues.ttl`, `OWA/3.0/transactiontypevalues.ttl` | Turtle syntax error: a `;` is missing after the `owl:imports` list, so the files could not be loaded. The `insert`, `delete` and `replace` transaction types also referenced `vers:transactionTypeScheme`, while the scheme is `type:transactionTypeScheme`. | `;` added; `skos:inScheme` set to `type:transactionTypeScheme` |

### Not changed

The OWA network uses 137 code-list classes (`…ClassValue`, `…FunctionValue`, `…UsageValue` and similar) as ranges without declaring them. This is systematic across all OWA modules, so it appears to be a property of the open-world transformation rather than an error; the CWA network declares the same classes as subclasses of `skos:Concept`.

## Verification

After these changes, checked with rdflib and an OWL 2 RL closure (owlrl):

* all 21 modules of each network parse (before, `transactiontypevalues.ttl` did not);
* the CWA network has no references to undefined terms; the OWA network's only undefined terms are the 137 code lists above;
* each whole network is consistent (no `owl:Nothing` members), including the CWA disjointness axiom that now applies to `doc:Document` and the workspace classes.