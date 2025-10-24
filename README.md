# neo4j-json-to-ttl

### Example usage
```shell
python src/main.py -i <json> -c <mapping_conf> -o <ttl>
```

## Mapping configuration

```yaml
base: <iri> # default IRI base for unprefixed (non-CURIE) values
prefixes: # prefixes are used when converting CURIE strings to IRIs
  <prefix>: <iri>
  ...
identifier_properties: # node properties in the list are assumed to hold a global identifier that can be converted to an IRI for the node
  - <property-name>
  ...
mappings:
  <property-or-label-or-value>: # all of the following properties are optional
    iri: <iri> # IRI to substitute for this text string
    base: <iri-base-overriding-global-base> # IRI base overriding global base for values (when key is property) or instances (when key is label)
    type: <'IRI' or iri-of-datatype> # if 'IRI' then the values for this property are transformed to IRIs; otherwise literals with the given datatype
```

### Mapping examples

Input Neo4j JSON node:
```json
{"type":"node","id":"95","labels":["Gene"],"properties":{"identifier":141,"ensembl":"ENSG00000144843","name":"ADPRH","description":"ADP-ribosylarginine hydrolase"}}
```

Config:
```yaml
base: 'https://purl.org/okn/frink/kg/spoke/'
identifier_properties:
  - 'identifier'
mappings:
  description:
    iri: 'http://www.w3.org/2000/01/rdf-schema#comment'
    type: 'http://www.w3.org/2001/XMLSchema#string'
  ensembl:
    type: IRI
    base: 'http://identifiers.org/ensembl/'
  name:
    iri: 'http://www.w3.org/2000/01/rdf-schema#label'
    type: 'http://www.w3.org/2001/XMLSchema#string'
  Gene:
    iri: 'https://w3id.org/biolink/vocab/Gene'
    base: 'http://www.ncbi.nlm.nih.gov/gene/'
```

Output RDF:
```turtle
<http://www.ncbi.nlm.nih.gov/gene/141> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/biolink/vocab/Gene> .
<http://www.ncbi.nlm.nih.gov/gene/141> <https://purl.org/okn/frink/kg/spoke/schema/ensembl> <http://identifiers.org/ensembl/ENSG00000144843> .
<http://www.ncbi.nlm.nih.gov/gene/141> <http://www.w3.org/2000/01/rdf-schema#label> "ADPRH"^^<http://www.w3.org/2001/XMLSchema#string> .
<http://www.ncbi.nlm.nih.gov/gene/141> <http://www.w3.org/2000/01/rdf-schema#comment> "ADP-ribosylarginine hydrolase"^^<http://www.w3.org/2001/XMLSchema#string> .
```
Because this node has a property in the `identifier_properties` list (`identifier`), the value of that property is used to construct an IRI for the node. The value (`141`) is not a CURIE, so it will be appended to the base to create the IRI. However, this node has a label (`Gene`) which is in the mappings dict and has its own base (`http://www.ncbi.nlm.nih.gov/gene/`), which overrides the global base. So the node IRI used as the subject for the output triples is `http://www.ncbi.nlm.nih.gov/gene/141`.

Node labels are interpreted as class assertions, and an IRI to use for `Gene` is provided in the mappings dict.

The `ensembl` property is in the mappings dict but does not have an `iri` key, so it is simply appended to the global base to get its IRI. It has a `type` value of `IRI`, so values for this property must themselves be converted to IRIs. It also has a `base` value, so that is combined with the property value `ENSG00000144843` to construct an IRI value `http://identifiers.org/ensembl/ENSG00000144843`.

Finally, `name` and `description` are both mapped to IRIs in the mappings dict, and both expect literal string values.
