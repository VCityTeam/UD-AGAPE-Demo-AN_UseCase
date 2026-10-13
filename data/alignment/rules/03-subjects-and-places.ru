# Record-level shortcuts and places.
#
# RiC pairs each n-ary relation with a direct property. Here every
#     reference of any state of a record yields rico:hasOrHadSubject from
#     the record to the referenced feature and to the rico:Place it is
#     located at. These shortcuts are derived and lossy (no dates, no purpose,
#     no state): the qualified link remains the reference (rules/02).
# BuildingParts and boundary surfaces inherit the location of their building.
# Run after 01 and 02.

PREFIX doc:  <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/Document/3.0/document#>
PREFIX bldg: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/building#>
PREFIX core: <https://dataset-dl.liris.cnrs.fr/rdf-owl-urban-data-ontologies/Ontologies/CityOWL/CWA/3.0/core#>
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>

# Propagate locations down to building parts and boundary surfaces
INSERT { ?part rico:hasOrHadLocation ?place }
WHERE {
  ?feature rico:hasOrHadLocation ?place ;
           (bldg:Building.buildingPart|core:AbstractSpace.boundary)+ ?part .
} ;

# Record -> subjects
INSERT {
  ?record rico:hasOrHadSubject ?target .
  ?target rico:isOrWasSubjectOf ?record .
  ?record rico:hasOrHadSubject ?place .
  ?place rico:isOrWasSubjectOf ?record .
}
WHERE {
  ?d doc:Document.referringTo ?ref ;
     rico:isOrWasInstantiationOf ?record .
  ?ref doc:Reference.referringTo ?target .
  OPTIONAL { ?target rico:hasOrHadLocation ?place }
}
