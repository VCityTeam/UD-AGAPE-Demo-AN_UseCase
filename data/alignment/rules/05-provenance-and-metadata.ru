# PROV-O and Dublin Core view of documents and references
#     (citygml3-prov.ttl, citygml3-dcterms.ttl), for stores without a reasoner.
#
# Each revision between two document states gets a prov:Activity
#     (<newer state>_generation) that used the older state and generated the
#     newer one. The data does not say what the activity was (digitisation,
#     restoration, annotation...) nor who performed it: attach prov:type,
#     rdfs:label and prov:wasAssociatedWith to these nodes when known.

PREFIX doc:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX core: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

# Document states: entities with a generation time, title and subjects
INSERT {
  ?d a prov:Entity ;
     prov:generatedAtTime ?created ;
     dct:title ?title ;
     dct:subject ?tag ;
     dct:identifier ?uri .
}
WHERE {
  ?d a doc:Document .
  OPTIONAL {
    ?d core:AbstractFeatureWithLifespan.creationDate ?created .
    FILTER(DATATYPE(?created) = xsd:dateTime)
  }
  OPTIONAL { ?d doc:Document.title ?title }
  OPTIONAL { ?d doc:Document.tag ?tag }
  OPTIONAL { ?d doc:Document.uri ?uri }
} ;

# References: entities generated when they were asserted, covering a period
INSERT {
  ?ref a prov:Entity ;
       prov:generatedAtTime ?asserted ;
       dct:temporal ?period .
}
WHERE {
  ?ref a doc:Reference .
  OPTIONAL {
    ?ref doc:Reference.referringDate ?asserted .
    FILTER(DATATYPE(?asserted) = xsd:dateTime)
  }
  OPTIONAL { ?ref doc:Reference.coveragePeriod ?period }
} ;

# Revisions: the activity that produced each newer document state
INSERT {
  ?activity a prov:Activity ;
            prov:used ?older ;
            prov:endedAtTime ?created .
  ?newer prov:wasGeneratedBy ?activity ;
         prov:wasDerivedFrom ?older .
}
WHERE {
  ?newer a doc:Document ;
         prov:wasRevisionOf ?older .
  OPTIONAL {
    ?newer core:AbstractFeatureWithLifespan.creationDate ?created .
    FILTER(DATATYPE(?created) = xsd:dateTime)
  }
  BIND(IRI(CONCAT(STR(?newer), "_generation")) AS ?activity)
}
