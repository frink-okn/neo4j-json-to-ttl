import argparse
import json
import pathlib
import logging
import sys

import rdflib
import yaml
import tempfile
from rdflib import Namespace, Graph, XSD, URIRef
from flatten_json import flatten

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

def  isURI(str):
    iri_prefixes = ['http:', 'https:', 'urn:', 'mailto:']
    if str:
        return False
    else:
        return (str.startswith(tuple(iri_prefixes)))

def create_node_id_mapping(base, node_namspace, id, mappings, mapping, property_mapping, prop_identifiers):

    node_id_mapping = {}
    # set up default
    node_id_mapping = {'iri': id, 'namespace': node_namspace}

    # change iri, if needed  (type = IRI or CURIE)
    # if iri gets changed, must save mapping from original id to new iri
    if 'type' in mappings[mapping] and mappings[mapping]['type'] in ['IRI', 'CURIE']:
        # check if it’s a CURIE using one of the defined prefixes
        if mapping in prop_identifiers:
            if isURI(property_mapping):
                node_id_mapping['iri'] = property_mapping
                node_id_mapping['namespace'] = property_mapping
            else: # it is a bare id
                # check to see if there is a base for this property value
                # if so, append it to that
                if 'base' in mappings[mapping]:
                    node_id_mapping['namespace'] = mappings[mapping]['base']
                    node_id_mapping['iri'] = node_id_mapping['namespace'] + property_mapping
                # if not, append it to the global base value
                else:
                    node_id_mapping['iri'] = base + property_mapping
                    node_id_mapping['namespace'] = base

    return node_id_mapping

def main(input: pathlib.Path, conf: pathlib.Path, output: pathlib.Path):
    logger.info(f"input: {input}, output: {output}")

    with open(input, 'r') as file, open(conf, 'r') as conf:
        conf_yaml = yaml.safe_load(conf)
        base = conf_yaml['base']
        
        schema_namespace = Namespace(base + "schema/")
        node_namespace = Namespace(base + "node/")
        relationship_namespace = Namespace(base + "relationship/")

        node_id_mappings = {}
        prop_identifiers = []
        if 'identifier_properties' in conf_yaml:
            prop_identifiers = conf_yaml['identifier_properties']
        mappings = conf_yaml['mappings']

        # open file to serial graph into
        ofd = open(output, 'a')

        for line in file:
            g = Graph()
            g.bind("sdo", "https://schema.org/")
            g.bind("schema", schema_namespace)
            g.bind("node", node_namespace)
            g.bind("relationship", relationship_namespace)

            value = json.loads(line)
            id = value["id"]
            t = value["type"]
            logger.debug(f"id: {id}, type: {t}")

            # some relationships don't have properties, so must check here - lisa
            if "properties" in value:
                properties = value["properties"]
            else:
                properties = {}
            properties = flatten(properties)

            if t == "node":

                for mapping in mappings:
                    if mapping in properties:
                        property_mapping = properties[mapping]
                        # skip triple if it has no value
                        if property_mapping != '':
                            property_mapping = str(property_mapping).replace('\n', '')
                            if not id in node_id_mappings:
                                node_id_mappings[id] = create_node_id_mapping(base, node_namespace, id, mappings, mapping, property_mapping, prop_identifiers)
                            if mapping not in prop_identifiers:
                                if mappings[mapping]['type'] == "IRI":
                                    if 'iri' in mappings[mapping]:
                                        predicate = mappings[mapping]['iri']
                                    else:
                                        predicate = node_id_mappings[id]['iri']
                                    if 'base' in mappings[mapping]:
                                        literal = mappings[mapping]['base'] + properties[mapping]
                                    else:
                                        literal = property_mapping
                                    # make sure there are no newlines in iris for predicate or literal
                                    literal = literal.replace('\n', '')
                                    predicate = predicate.replace('\n', '')
                                    g.add((rdflib.term.URIRef(node_id_mappings[id]['iri'], node_id_mappings[id]['namespace']), URIRef(predicate), URIRef(literal)))
                                else:
                                    if 'iri' in mappings[mapping]:
                                        iriref = mappings[mapping]['iri']
                                    else:
                                        iriref = schema_namespace + mapping
                                    # make sure there are no newlines in iri
                                    iriref = iriref.replace('\n', '')
                                    g.add((rdflib.term.URIRef(node_id_mappings[id]['iri'], node_id_mappings[id]['namespace']), URIRef(iriref), rdflib.Literal(property_mapping, datatype=URIRef(mappings[mapping]['type']))))

                labels = value["labels"]
                for label in labels:
                    # set default namespace
                    label_namespace = schema_namespace
                    if label in mappings and 'iri' in mappings[label]:
                        label_namespace = mappings[label]['iri']
                    g.add((rdflib.term.URIRef(node_id_mappings[id]['iri'], node_id_mappings[id]['namespace']), rdflib.namespace.RDF.type, rdflib.term.URIRef(label, label_namespace)))

            if t == "relationship":

                label = value["label"]
                label_namespace = schema_namespace
                if label in mappings and 'iri' in mappings[label]:
                    label_namespace = ""
                    label = mappings[label]['iri']
                start_id = value["start"]["id"]
                end_id = value["end"]["id"]
                rel_id = id

                g.add((rdflib.term.URIRef(node_id_mappings[start_id]['iri'], node_id_mappings[start_id]['namespace']), rdflib.term.URIRef(label, label_namespace), rdflib.term.URIRef(node_id_mappings[end_id]['iri'], node_id_mappings[end_id]['namespace'])))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.subject, rdflib.term.URIRef(node_id_mappings[start_id]['iri'], node_id_mappings[start_id]['namespace'])))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.predicate, rdflib.term.URIRef(label, label_namespace)))
                g.add((rdflib.term.URIRef(rel_id, relationship_namespace), rdflib.namespace.RDF.object, rdflib.term.URIRef(node_id_mappings[end_id]['iri'], node_id_mappings[end_id]['namespace'])))
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

            # Serialize and append to file
            ofd.write(g.serialize(format="nt"))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='neo4j json to ttl')
    parser.add_argument('-i', '--input', required=True, type=pathlib.Path, help='A json file from a Neo4j export')
    parser.add_argument('-c', '--conf', required=True, type=pathlib.Path, help='One of the yaml files found in conf')
    parser.add_argument('-o', '--output', required=True, type=pathlib.Path, help='A Turtle file')

    args = parser.parse_args()

    main(args.input, args.conf, args.output)
