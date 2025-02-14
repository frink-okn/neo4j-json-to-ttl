import argparse
import json
import pathlib
import logging
import sys

import rdflib
import yaml
from rdflib import Namespace, Graph, XSD, IdentifiedNode, URIRef
# from rdflib.extras.describer import cast_value, Describer
# from rdflib.namespace import NamespaceManager

logger = logging.getLogger(__name__)
# logger.addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        # logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def main(input: pathlib.Path, conf: pathlib.Path, output: pathlib.Path):
    logger.info(f"input: {input}, output: {output}")

    with open(input, 'r') as file, open(conf, 'r') as conf:
        conf_yaml = yaml.safe_load(conf)
        base = conf_yaml['base']
        # base_namespace = Namespace(base)
        schema_namespace = Namespace(base + "schema/")
        node_namespace = Namespace(base + "node/")
        relationship_namespace = Namespace(base + "relationship/")

        # g = Graph(base=base_namespace)
        g = Graph()
        g.bind("sdo", "https://schema.org/")
        g.bind("schema", schema_namespace)
        g.bind("node", node_namespace)
        g.bind("relationship", relationship_namespace)

        # print(g.serialize(format="turtle"))

        mappings = conf_yaml['mappings']

        for line in file:
            value = json.loads(line)
            id = value["id"]
            t = value["type"]
            logger.debug(f"id: {id}, type: {t}")

            # some relationships don't have properties, so must check here - lisa
            if "properties" in value:
                properties = value["properties"]
            else:
                properties = {}

            if t == "node":
                # construct iri for node
                iri = id
                if "identifier" in properties:
                    iri = properties["identifier"]

                for mapping in mappings:
                    if mapping in properties:
                        property_mapping = properties[mapping]
                        property_mapping = str(property_mapping).replace('\n', '')

                        if 'iri' not in mappings[mapping]:
                            mappings[mapping]['iri'] = schema_namespace + mapping
                        g.add((rdflib.term.URIRef(iri, node_namespace), URIRef(mappings[mapping]['iri']), rdflib.Literal(property_mapping, datatype=URIRef(mappings[mapping]['type']))))

                labels = value["labels"]
                for label in labels:
                    g.add((rdflib.term.URIRef(iri, node_namespace), rdflib.namespace.RDF.type, rdflib.term.URIRef(label, schema_namespace)))

            if t == "relationship":

                label = value["label"]
                start_id = value["start"]["id"]
                end_id = value["end"]["id"]
                rel_id = id

                g.add((rdflib.term.URIRef(start_id, node_namespace), rdflib.term.URIRef(label, schema_namespace), rdflib.term.URIRef(end_id, node_namespace)))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.subject, rdflib.term.URIRef(start_id, node_namespace)))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.predicate, rdflib.term.URIRef(label, schema_namespace)))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.object, rdflib.term.URIRef(end_id, node_namespace)))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.type, rdflib.namespace.RDF.Statement))

                for mapping_key, mapping_value in mappings.items():
                    try:

                        if not mapping_key in properties:
                            continue

                        property_mapping_value = properties[mapping_key]
                        logger.debug(f"mapping: {mapping_value}, value: {property_mapping_value}, value type: {type(property_mapping_value)}")

                        if 'iri' not in mapping_value:
                            g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.term.URIRef(mapping, schema_namespace), rdflib.Literal(property_mapping_value, datatype=URIRef(mapping_value['type']))))

                        else:

                            if mapping_value['type'] == 'IRI':
                                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), URIRef(mapping_value['iri']), rdflib.term.URIRef(f"{property_mapping_value}")))

                            else:

                                if rdflib.XSD.dateTime.eq(URIRef(mapping_value['type'])):

                                    if "T" in property_mapping_value:
                                        g.add((rdflib.term.URIRef(rel_id, relationship_namespace), URIRef(mapping_value['iri']), rdflib.Literal(property_mapping_value, datatype=rdflib.XSD.dateTime)))
                                    else:
                                        g.add((rdflib.term.URIRef(rel_id, relationship_namespace), URIRef(mapping_value['iri']), rdflib.Literal(property_mapping_value, datatype=XSD.date)))

                                else:
                                    g.add((rdflib.term.URIRef(rel_id, relationship_namespace), URIRef(mapping_value['iri']), rdflib.Literal(property_mapping_value, datatype=URIRef(mapping_value['type']))))
                    except:
                        logger.exception("error")

        g.serialize(destination=output)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='neo4j json to ttl')
    parser.add_argument('-i', '--input', required=True, type=pathlib.Path, help='A json file from a Neo4j export')
    parser.add_argument('-c', '--conf', required=True, type=pathlib.Path, help='One of the yaml files found in conf')
    parser.add_argument('-o', '--output', required=True, type=pathlib.Path, help='A Turtle file')

    args = parser.parse_args()

    main(args.input, args.conf, args.output)
