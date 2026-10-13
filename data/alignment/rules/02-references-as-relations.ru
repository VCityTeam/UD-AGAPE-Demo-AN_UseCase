# doc:Reference as a qualified rico:Relation (DocGraph R3, R4, R5).
#
# The reference node itself becomes the RiC relation: its source is the
#     document state, its target the urban feature (any
#     core:AbstractFeatureWithLifespan: facade, building, district...).
# Both dates of the dual timeline are kept as rico:Date nodes:
#   - coverage period (the OWL-Time interval node itself, also typed rico:Date)
#   - assertion date  (<reference>_assertionDate)
# This materialises the TBox axioms of citygml3-rico.ttl for stores without
#     a reasoner, and adds the date mapping. Purpose types given as plain
#     literals instead of doc:PurposeTypeValue concepts are not mapped.

PREFIX doc:   <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX rico:  <https://www.ica.org/standards/RiC/ontology#>
PREFIX time:  <http://www.w3.org/2006/time#>
PREFIX align: <https://raw.githubusercontent.com/VCityTeam/UD-AGAPE-Demo-AN_UseCase/master/data/alignment/citygml3-rico.ttl#>

# Source, target, interpretation and purpose
INSERT {
  ?ref a rico:Relation ;
       rico:relationHasSource ?d ;
       rico:relationHasTarget ?target ;
       rico:generalDescription ?text ;
       rico:hasOrHadType ?purpose .
  ?d rico:thingIsSourceOfRelation ?ref .
  ?target rico:thingIsTargetOfRelation ?ref .
}
WHERE {
  ?d doc:Document.referringTo ?ref .
  ?ref a doc:Reference .
  OPTIONAL { ?ref doc:Reference.referringTo ?target }
  OPTIONAL { ?ref doc:Reference.referenceText ?text }
  OPTIONAL { ?ref doc:Reference.purposeType ?purpose FILTER(isIRI(?purpose)) }
} ;

# Coverage period: the depicted city state
INSERT {
  ?period a rico:Date ;
          rico:hasDateType align:dateType_coveragePeriod ;
          rico:normalizedDateValue ?normalized .
  ?ref rico:relationHasDate ?period .
  ?period rico:isDateAssociatedWithRelation ?ref .
}
WHERE {
  ?ref a doc:Reference ;
       doc:Reference.coveragePeriod ?period .
  OPTIONAL {
    ?period time:hasBeginning ?b .
    OPTIONAL { ?b time:inXSDgYear ?bY }
    OPTIONAL { ?b time:inXSDgYearMonth ?bYM }
    OPTIONAL { ?b time:inXSDDate ?bD }
    OPTIONAL { ?b time:inXSDDateTimeStamp ?bDT }
  }
  OPTIONAL {
    ?period time:hasEnd ?e .
    OPTIONAL { ?e time:inXSDgYear ?eY }
    OPTIONAL { ?e time:inXSDgYearMonth ?eYM }
    OPTIONAL { ?e time:inXSDDate ?eD }
    OPTIONAL { ?e time:inXSDDateTimeStamp ?eDT }
  }
  BIND(COALESCE(STR(?bY), STR(?bYM), STR(?bD), STR(?bDT)) AS ?begin)
  BIND(COALESCE(STR(?eY), STR(?eYM), STR(?eD), STR(?eDT)) AS ?end)
  BIND(IF(?begin = ?end, ?begin, CONCAT(?begin, "/", ?end)) AS ?normalized)
} ;

# Assertion date: when the reference was asserted
INSERT {
  ?assertion a rico:Date ;
             rico:hasDateType align:dateType_assertion ;
             rico:normalizedDateValue ?when .
  ?ref rico:relationHasDate ?assertion .
  ?assertion rico:isDateAssociatedWithRelation ?ref .
}
WHERE {
  ?ref a doc:Reference ;
       doc:Reference.referringDate ?date .
  BIND(STR(?date) AS ?when)
  BIND(IRI(CONCAT(STR(?ref), "_assertionDate")) AS ?assertion)
}
