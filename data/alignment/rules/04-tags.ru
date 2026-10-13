# Tags as subject concepts (DocGraph R2: first indexing layer for retrieval
#     and thematic organisation).
# Run after 01.

PREFIX doc:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>

INSERT {
  ?tag a rico:Concept ;
       rico:name ?text .
  ?record rico:hasOrHadSubject ?tag .
  ?tag rico:isOrWasSubjectOf ?record .
}
WHERE {
  ?d doc:Document.tag ?tag ;
     rico:isOrWasInstantiationOf ?record .
  FILTER(isIRI(?tag))     # tags given as plain literals are not doc:Tag objects
  OPTIONAL { ?tag doc:Tag.text ?text }
}
