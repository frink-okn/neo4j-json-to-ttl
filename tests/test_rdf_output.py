import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from rdflib import Graph
from rdflib.compare import isomorphic
from main import main

# Base directories for test data
BASE_DIR = pathlib.Path(__file__).parent
TEST_JSON_DIR = BASE_DIR / "test-json"
TEST_CONFIG_DIR = BASE_DIR / "test-config"
TEST_RDF_DIR = BASE_DIR / "test-rdf"


def get_test_cases():
    """Return all base names (without extension) from the test-json directory."""
    return [p.stem for p in TEST_JSON_DIR.glob("*.json")]


@pytest.mark.parametrize("name", get_test_cases())
def test_rdf_output_matches_expected(tmp_path, name):
    """Test that the generated RDF graph is isomorphic to the expected graph."""
    input_json = TEST_JSON_DIR / f"{name}.json"
    config_file = TEST_CONFIG_DIR / f"{name}.yaml"
    expected_rdf = TEST_RDF_DIR / f"{name}.ttl"
    output_file = tmp_path / f"{name}.ttl"

    assert input_json.exists(), f"Missing input file: {input_json}"
    assert config_file.exists(), f"Missing config file: {config_file}"
    assert expected_rdf.exists(), f"Missing expected TTL file: {expected_rdf}"

    main(input=input_json, conf=config_file, output=output_file)

    g_generated = Graph().parse(output_file, format="turtle")
    g_expected = Graph().parse(expected_rdf, format="turtle")

    assert isomorphic(g_generated, g_expected), f"RDF triples differ for {name}"
