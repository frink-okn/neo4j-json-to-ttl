import argparse
import json
import pathlib
import logging
import sys

import rdflib
import yaml
import tempfile
from rdflib import Namespace, Graph, Literal, XSD, URIRef
from rdflib.namespace import RDF
from collections.abc import Sequence

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
        schema_namespace = Namespace(base + "schema/")
        node_namespace = Namespace(base + "node/")
        relationship_namespace = Namespace(base + "relationship/")
        node_id_mappings = {}
        
        # open file to serialize graph into
        with open(output, 'w') as ofd:
            for line in file:
                graph = Graph()
                jsonline = json.loads(line)
                t = jsonline["type"]
                logger.debug(f"id: {id}, type: {t}")

                if t == "node":
                    handle_node(jsonline, conf_yaml, node_namespace, schema_namespace, node_id_mappings, graph)
                elif t == "relationship":
                    handle_relationship(jsonline, conf_yaml, node_namespace, relationship_namespace, schema_namespace, node_id_mappings, graph)
                ofd.write(graph.serialize(format="nt"))

def handle_node(jsonline, conf_yaml, node_namespace, schema_namespace, node_id_mappings, graph):
    local_id = jsonline["id"]
    props = jsonline.get("properties", {})
    id_props = conf_yaml.get("identifier_properties", [])
    node_id_value = None
    if id_props:
        node_id_value = next((props[key] for key in id_props if key in props), None)
    if node_id_value:
        uri_text = asURI(node_id_value, conf_yaml, node_namespace, jsonline['labels'])
        if uri_text is not None:
            node_iri = URIRef(uri_text)
        else:
            node_iri = node_namespace[local_id]
    else:
        node_iri = node_namespace[local_id]
    node_id_mappings[local_id] = node_iri
    for class_name in jsonline['labels']:
        class_uri = URIRef(asURI(class_name, conf_yaml, schema_namespace))
        graph.add((node_iri, RDF.type, class_uri))
    handle_properties(node_iri, props, conf_yaml, node_namespace, schema_namespace, node_id_mappings, graph)

def handle_relationship(jsonline, conf_yaml, node_namespace, relationship_namespace, schema_namespace, node_id_mappings, graph):
    pred = URIRef(asURI(jsonline['label'], conf_yaml, schema_namespace))
    subj = node_id_mappings[jsonline['start']['id']]
    obj = node_id_mappings[jsonline['end']['id']]
    graph.add((subj, pred, obj))
    if 'properties' in jsonline and jsonline['properties']:
        rel_uri = URIRef(asURI(jsonline['id'], conf_yaml, relationship_namespace))
        graph.add((rel_uri, RDF.type, RDF.Statement))
        graph.add((rel_uri, RDF.subject, subj))
        graph.add((rel_uri, RDF.predicate, pred))
        graph.add((rel_uri, RDF.object, obj))
        props = jsonline['properties']
        handle_properties(rel_uri, props, conf_yaml, node_namespace, schema_namespace, node_id_mappings, graph)

def handle_properties(node_iri, props, conf_yaml, node_namespace, schema_namespace, node_id_mappings, graph):
    id_props = conf_yaml.get("identifier_properties", [])
    for prop, value in props.items():
        if isinstance(value, Sequence) and not isinstance(value, str):
            values = value
        else:
            values = [value]
        for value in values:
            if prop not in id_props:
                prop_uri = asURI(prop, conf_yaml, schema_namespace)
                if prop_uri is None:
                    logger.error(f"Didn't make a URI for predicate {prop}")
                predicate = URIRef(prop_uri)
                vt = value_type(prop, conf_yaml)
                if vt == 'IRI':
                    local_base = node_namespace
                    if prop in conf_yaml['mappings'] and 'base' in conf_yaml['mappings'][prop]:
                        local_base = conf_yaml['mappings'][prop]['base']
                    maybe_uri = asURI(value, conf_yaml, local_base)
                    if maybe_uri:
                        prop_value = URIRef(maybe_uri)
                    else:
                        logger.warn(f"Creating literal for value '{value}' but we wanted an IRI for predicate {predicate}")
                        prop_value = Literal(value)
                elif vt is not None:
                    if vt == 'http://www.w3.org/2001/XMLSchema#boolean':
                        try:
                            bool_value = str_to_bool(value)
                            prop_value = Literal(bool_value)
                        except:
                            prop_value = Literal(value) #format problem; just put in as plain literal
                    else:
                        literal = Literal(value, datatype=URIRef(vt))
                        if literal.value is not None:
                            prop_value = literal
                        else:
                            prop_value = Literal(value) #format problem; just put in as plain literal
                else:
                    prop_value = Literal(value)
                graph.add((node_iri, predicate, prop_value))

def asURI(text, conf, default_base, class_labels=[]):
    text = str(text)
    if text.startswith('http') or text.startswith('urn:') or text.startswith('mailto:'):
        return text
    elif text in conf['mappings'] and 'iri' in conf['mappings'][text]:
        return conf['mappings'][text]['iri']
    elif not any(c.isspace() for c in text) and ":" in text:
        pieces = text.split(":", maxsplit=1)
        if conf['prefixes'][pieces[0]]:
            base = conf['prefixes'][pieces[0]]
            return f"{base}{pieces[1]}"
    elif not any(c.isspace() for c in text):
        base = next(
            (conf['mappings'][label]['base'] for label in class_labels if label in conf['mappings'] and 'base' in conf['mappings'][label]),
            default_base
        )
        return f"{base}{text}"
    else:
        return None

def value_type(prop, conf_yaml):
    if prop in conf_yaml['mappings']:
        prop_dict = conf_yaml['mappings'][prop]
        if 'type' in prop_dict:
            return prop_dict['type']
    return None

def str_to_bool(val):
    """Convert a string representation of truth to true or false.
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = str(val).lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='neo4j json to ttl')
    parser.add_argument('-i', '--input', required=True, type=pathlib.Path, help='A json file from a Neo4j export')
    parser.add_argument('-c', '--conf', required=True, type=pathlib.Path, help='One of the yaml files found in conf')
    parser.add_argument('-o', '--output', required=True, type=pathlib.Path, help='A Turtle file')

    args = parser.parse_args()

    main(args.input, args.conf, args.output)
