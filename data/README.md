# Data

Urban documentation data for the Archives nationales use case, and its alignment with archival description (RiC-O). Everything here uses the ontologies in [`../ontologies`](../ontologies/README.md): CityGML 3.0 terms come from CityOWL CWA 3.0, document terms from its `document` module.

| Folder | Content |
|---|---|
| [`gratteciel/`](gratteciel/) | City objects of the Cité des Gratte-Ciel (Villeurbanne), the documents that describe them (Document ontology) and their LoD2 geometry |
| [`alignment/`](alignment/README.md) | Alignment of that data with RiC-O 1.1, PROV-O and Dublin Core: mappings, rules, place authority, example queries, and scripts to apply and validate it |
| [`viewer/`](viewer/README.md) | iTowns 3D viewer of the buildings, on IGN terrain and aerial imagery (current or 1950–1965), with the documents that refer to them; built from the aligned data |

## The Gratte-Ciel dataset

[`gratteciel/gratteciel-documents.ttl`](gratteciel/gratteciel-documents.ttl) (483 triples) is a small corpus of real documents about the Cité des Gratte-Ciel in Villeurbanne: the residential ensemble by Môrice Leroux, built 1931–1934, and its town hall by Robert Giroud, inaugurated in 1934.

### Documents

Every document, URL, title, author, licence and date comes from its source (checked on 2026-10-12 and 2026-10-13; [`gratteciel/source_metadata.py`](gratteciel/source_metadata.py) prints the metadata used):

| Document | States (`doc:Document`, linked by `prov:wasRevisionOf`) | Source |
|---|---|---|
| 1. *Vue aérienne de la cité des Gratte-Ciel en 1936* | the 1936 photograph (Centre du Rize, Villeurbanne) → its digitisation, 2020-03-11, published on Wikimedia Commons 2020-09-28 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Vue_a%C3%A9rienne_de_la_cit%C3%A9_des_Gratte-Ciel_en_1936.jpg), CC BY-SA 4.0 |
| 2. *Montage de la charpente des Gratte-Ciel de Villeurbanne en janvier 1932*, Jules Sylvestre | the January 1932 photograph → its record in Numelyo, digital library of the Bibliothèque municipale de Lyon → its copy on Wikimedia Commons, 2025-02-22 | [Numelyo](https://numelyo.bm-lyon.fr/BML:BML_01ICO001014cd177ad8ced7), [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Montage_de_la_charpente_des_GratteCiel_de_Villeurbanne_en_janvier_1932.jpg), public domain |
| 3. *Cité, dite les Gratte-ciel*, heritage inventory record ACR0000160, label "Architecture contemporaine remarquable" (2003) | the record, online since 2020-08-04 | [POP, base Mérimée](https://pop.culture.gouv.fr/notice/merimee/ACR0000160), Ministère de la Culture |
| 4. *Tours Gratte Ciel Avenue Henri Barbusse*, 2023-12-28 | the photograph | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Tours_Gratte_Ciel_Avenue_Henri_Barbusse_-_Villeurbanne_(FR69)_-_2023-12-28_-_1.jpg), CC BY-SA 4.0 |
| 5. *Hôtel de ville*, historic monument record PA00118150 (partially listed on 29 April 1991) | the record, online since 1993-12-03 | [POP, base Mérimée](https://pop.culture.gouv.fr/notice/merimee/PA00118150), Ministère de la Culture |
| 6. *Plan façade Nord de l'hôtel de ville de Villeurbanne*, elevation drawing, Florian Faivre-Malfroy, 2013 | the drawing | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Plan_fa%C3%A7ade_Nord_de_l%27h%C3%B4tel_de_ville_de_Villeurbanne.png), CC BY-SA 3.0 |
| 7. *L'Hôtel de ville de Villeurbanne, couloir*, Jules Sylvestre, "vers 1930" | the photograph → its Numelyo record → its copy on Wikimedia Commons, 2022-07-28 | [Numelyo](https://numelyo.bm-lyon.fr/BML:BML_01ICO001014cd15f98f225d), [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:L%27H%C3%B4tel_de_ville_de_Villeurbanne,_couloir.jpg), public domain |
| 8. *Hôtel de ville de Villeurbanne façade sud*, CHABERT Louis, 2020-06-01 | the photograph | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:H%C3%B4tel_de_ville_de_Villeurbanne_fa%C3%A7ade_sud.jpg), CC BY-SA 4.0 |
| 9. *Hôtel de Ville Place Liberation*, Alexmar983, 2008-05-21 | the photograph | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:H%C3%B4tel_de_Ville_Place_Liberation_PA00118150.jpg), CC BY-SA 3.0 |
| 10. *Hôtel Ville - Villeurbanne*, Chabe01, 2023-12-28 | the photograph | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:H%C3%B4tel_Ville_-_Villeurbanne_(FR69)_-_2023-12-28_-_2.jpg), CC BY-SA 4.0 |

Authors and licences are recorded with `dct:creator`, `dct:publisher` and `dct:license`. A date given only as a year or a month is stored as the first day of that period, with a comment saying so.

### City objects and references

* **City objects**, at three scales:
  * the district `data:GratteCielDistrict`, dated 1930 from its Mérimée record ACR0000160;
  * 5 buildings: the 4 Gratte-Ciel blocks `data:BU_69266BO56_0` … `_3` (not dated individually by the sources) and the town hall `data:BU_69266BO55_0`, created 1934 (inauguration, Mérimée PA00118150). The town hall was identified in the 3D city model as the building whose footprint contains the record's coordinates; its 64 m height matches the belfry the record describes;
  * 2 surfaces: the town hall's LoD2 wall surface (`data:WallSurface_60`, its façades) and roof surface (`data:RoofSurface_60`, its roofs).
* **References**: 16 `doc:Reference`s, each with a reference text, a purpose type, the period depicted (OWL-Time interval) and the date the link was asserted. The aerial photograph refers to the 4 Gratte-Ciel blocks, as in the DocGraph case study (asserted 2020-03-11), and to the district (added 2026-10-12). Documents 2–4 refer to the district, because their sources do not say which building they show. The town hall documents refer to the building, or to its façades and roofs when that is what they show or protect.
* **Vocabularies**: 9 tags (`doc:Tag`) and 6 purpose types (`doc:PurposeTypeValue`, in a SKOS concept scheme): aerial view, construction photograph, heritage inventory record, street view, architectural drawing, interior view.

The references are this dataset's own annotations; the other facts come from the sources above.

### How the case study covers the five requirements

The requirements are those of the Document model (DocGraph, 3DGeoInfo 2026):

| Requirement | In this dataset |
|---|---|
| **R1** documents as urban features | 15 document states, all `core:AbstractFeatureWithLifespan` with their own creation dates, next to the city objects they describe |
| **R2** heterogeneous documents | aerial, construction, street and interior photographs; an architectural drawing; two heritage inventory records; from Wikimedia Commons, the Bibliothèque municipale de Lyon and the Ministry of Culture |
| **R3** document versions | three version chains: the 1936 aerial view (original → digitisation) and two Jules Sylvestre photographs (original → Numelyo → Wikimedia Commons) |
| **R4** document time vs city time | depicted periods from c. 1930 to 2023, assertion dates from 2020 to 2026, and city-object dates (district 1930, town hall 1934). One reference shows a conflict: the corridor photograph is dated "vers 1930" by its library while the town hall was inaugurated in 1934, so that reference carries `rico:relationCertainty "uncertain"` |
| **R5** multi-scale references | district (4 references), buildings (8) and surfaces (4): the façades and roofs protected in 1991, the north façade drawing and the south façade photograph |

### 3D geometry

[`gratteciel/gratteciel-geometry.ttl`](gratteciel/gratteciel-geometry.ttl) (2.2 MB) holds the LoD2 roofs and walls of the 92 buildings within 200 m of the Gratte-Ciel, extracted from the UD-Graph 3D city model `GratteCiel_2018_split_v3` and rewritten with the CityOWL CWA vocabulary: building → `core:AbstractSpace.boundary` → `con:RoofSurface` / `con:WallSurface` → `core:AbstractThematicSurface.lod2MultiSurface` (a sub-property of `geo:hasGeometry`) → GML multi-surface (`geo:asGML`, EPSG:3946).

The geometry and the documents use the same building and surface IRIs (those of the 3D city model), so loading both joins them: a query can go from a document to its references, to the buildings they target, the buildings whose surfaces they target, or the buildings of the place they target, to their LoD2 surfaces ([`alignment/queries/documents-with-geometry.rq`](alignment/queries/documents-with-geometry.rq)). The [3D viewer](viewer/README.md) is built on this join.

## Quick start

From the repository root, with Python 3:

```bash
python3 -m venv .venv
.venv/bin/pip install rdflib owlrl

# Align the data (RiC-O, PROV-O, Dublin Core views) into one file
.venv/bin/python data/alignment/materialize.py aligned.ttl data/gratteciel/gratteciel-documents.ttl

# Check documents and geometry against the closed-world or open-world CityOWL network
.venv/bin/python data/alignment/validate.py --network cwa data/gratteciel/gratteciel-documents.ttl data/gratteciel/gratteciel-geometry.ttl
.venv/bin/python data/alignment/validate.py --network owa data/gratteciel/gratteciel-documents.ttl data/gratteciel/gratteciel-geometry.ttl

# Explore in 3D, then open http://localhost:8000
cd data/viewer && python3 -m http.server 8000
```

Both validations pass. See [`alignment/README.md`](alignment/README.md) for the mappings, the queries and their results.
