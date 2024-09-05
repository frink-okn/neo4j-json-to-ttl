import argparse
import json
import pathlib
import logging
import sys
import rdflib
from rdflib import Namespace, Graph, XSD
from rdflib.namespace import NamespaceManager

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

def main(input: pathlib.Path, output: pathlib.Path):
    logger.info(f"input: {input}, output: {output}")

    wokn = Namespace("https://wildlife.proto-okn.net/kg/")

    namespace_manager = NamespaceManager(Graph())
    namespace_manager.bind('wokn', wokn, override=False)

    g = Graph(base="https://wildlife.proto-okn.net/kg/")
    g.namespace_manager = namespace_manager

    with open(input, 'r') as file:
        for line in file:
            value = json.loads(line)
            id = value["id"]
            t = value["type"]
            # logger.info(f"id: {id}, type: {t}")
            if t == "node":
                property_name = value["properties"]["name"]
                property_name = str(property_name).replace('\n', '')
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDFS.label, rdflib.Literal(property_name, datatype=XSD.string)))
                labels = value["labels"]
                for label in labels:
                    g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDF.type, rdflib.term.URIRef(label, wokn)))

            if t == "relationship":
                label = value["label"]

                properties_multimedia = value["properties"]["multimedia"]
                properties_dates = value["properties"]["dates"]
                properties_observed_times = value["properties"]["observed_times"]

                start_id = value["start"]["id"]
                # start_labels = value["start"]["labels"]
                # start_properties = value["start"]["properties"]
                # start_properties_name = value["start"]["properties"]["name"]

                end_id = value["end"]["id"]
                # end_labels = value["end"]["labels"]
                # start_properties = value["end"]["properties"]
                # start_properties_name = value["end"]["properties"]["name"]

                g.add((rdflib.term.URIRef(start_id, wokn), rdflib.term.URIRef(label, wokn), rdflib.term.URIRef(end_id, wokn)))
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDF.type, rdflib.namespace.RDF.Statement))
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDF.subject, rdflib.term.URIRef(start_id, wokn)))
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDF.predicate, rdflib.term.URIRef(label, wokn)))
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.RDF.object, rdflib.term.URIRef(end_id, wokn)))
                g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.SDO.subjectOf, rdflib.term.URIRef(f"{properties_multimedia}")))
                if "T" in properties_dates:
                    g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.DCTERMS.date, rdflib.Literal(properties_dates, datatype=XSD.dateTime)))
                else:
                    g.add((rdflib.term.URIRef(id, wokn), rdflib.namespace.DCTERMS.date, rdflib.Literal(properties_dates, datatype=XSD.date)))

                g.add((rdflib.term.URIRef(id, wokn), rdflib.term.URIRef("observed_times", wokn), rdflib.Literal(properties_observed_times, datatype=XSD.dateTime)))

                # break

    g.serialize(destination=output)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='neo4j json-ld to ttl')
    parser.add_argument('-i', '--input', required=True, type=pathlib.Path, help='A json-ld file from a Neo4j export')
    parser.add_argument('-o', '--output', required=True, type=pathlib.Path, help='A Turtle file')

    args = parser.parse_args()

    main(args.input, args.output)
