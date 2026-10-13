# Document identity and document states (DocGraph R1, R3).
#
# Each doc:Document is one documentary state (scan, restoration, annotated
#     version...) with its own media URI and lifespan: a rico:Instantiation.
# Each prov:wasRevisionOf chain shares one stable documentary identity:
#     a rico:Record, named after the oldest state (<root>_record) so that
#     adding a newer state later does not change the record IRI. Its title
#     is the title of the newest state.
#
# doc:Document itself is not retyped by an OWL axiom: it remains a
#     core:AbstractFeatureWithLifespan as defined by the Document ontology.

PREFIX doc:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX core: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/core#>
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX prov: <http://www.w3.org/ns/prov#>

# Document states -> instantiations
INSERT {
  ?d a rico:Instantiation ;
     rico:title ?title ;
     rico:identifier ?uri ;
     rico:creationDate ?created .
}
WHERE {
  ?d a doc:Document .
  OPTIONAL { ?d doc:Document.title ?title }
  OPTIONAL { ?d doc:Document.uri ?uri }
  OPTIONAL { ?d core:AbstractFeatureWithLifespan.creationDate ?created }
} ;

# One record per version chain, titled after its newest state
INSERT {
  ?record a rico:Record ;
          rico:title ?headTitle ;
          rico:hasOrHadInstantiation ?d ;
          rico:hasOrHadDigitalInstantiation ?d .
  ?d rico:isOrWasInstantiationOf ?record ;
     rico:isOrWasDigitalInstantiationOf ?record .
}
WHERE {
  ?d a doc:Document ;
     prov:wasRevisionOf* ?root .
  ?root a doc:Document .
  FILTER NOT EXISTS { ?root prov:wasRevisionOf ?older }
  BIND(IRI(CONCAT(STR(?root), "_record")) AS ?record)
  OPTIONAL {
    ?head prov:wasRevisionOf* ?root ;
          doc:Document.title ?headTitle .
    FILTER NOT EXISTS { ?newer prov:wasRevisionOf ?head }
  }
} ;

# Documentary history: older state -> derived state
INSERT {
  ?older rico:hasOrHadDerivedInstantiation ?newer .
  ?newer rico:isOrWasDerivedFromInstantiation ?older .
}
WHERE {
  ?newer a doc:Document ;
         prov:wasRevisionOf ?older .
  ?older a doc:Document .
}
