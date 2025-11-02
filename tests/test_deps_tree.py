import os
import sys
from pathlib import Path
import json
import pytest

# Ensure src is on sys.path so we can import deps_tree
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import deps_tree as dt

TEST_DATA = Path(__file__).resolve().parent / 'data'

def test_find_poms_in_dir():
    """Test finding POMs in a directory structure"""
    # Get all POMs
    poms = dt.find_poms_in_dir(TEST_DATA)
    
    # Should find exactly 3 POMs - one in data dir, one in repo_a, one in repo_b
    assert len(poms) == 3
    
    # Verify all found paths exist and are actually pom.xml files
    for pom in poms:
        assert pom.exists()
        assert pom.name == 'pom.xml'
    
    # Verify we found the specific expected POMs
    expected_poms = {
        TEST_DATA / 'pom.xml',
        TEST_DATA / 'repo_a' / 'pom.xml',
        TEST_DATA / 'repo_b' / 'pom.xml'
    }
    assert set(poms) == expected_poms

def test_find_poms_in_empty_dir(tmp_path):
    """Test finding POMs in an empty directory"""
    poms = dt.find_poms_in_dir(tmp_path)
    assert len(poms) == 0

def test_find_poms_in_dir_with_no_poms(tmp_path):
    """Test finding POMs in a directory that has files but no POMs"""
    # Create some non-POM files
    (tmp_path / 'file1.txt').touch()
    (tmp_path / 'file2.xml').touch()
    os.mkdir(tmp_path / 'subdir')
    (tmp_path / 'subdir' / 'other.xml').touch()
    
    poms = dt.find_poms_in_dir(tmp_path)
    assert len(poms) == 0

def test_generate_plant_uml():
    """Test PlantUML graph generation with a simple dependency graph"""
    # Build a simple test graph
    G = dt.build_dependency_graph(TEST_DATA)
    plantuml = dt.generate_plant_uml(G)
    
    # Verify the basic structure
    assert plantuml.startswith('@startuml')
    assert plantuml.endswith('@enduml')
    assert 'digraph G {' in plantuml
    
    # Verify that root projects and leaf dependencies are grouped in clusters
    assert 'subgraph cluster_roots' in plantuml
    assert 'subgraph cluster_leaves' in plantuml
    
    # Verify that nodes and edges are properly formatted
    for node in G.nodes:
        assert f'"{node}" [shape=box, style=rounded]' in plantuml
    for src, dst in G.edges:
        assert f'"{src}" -> "{dst}";' in plantuml

def test_generate_json():
    """Test JSON graph generation with a simple dependency graph"""
    # Build a simple test graph
    G = dt.build_dependency_graph(TEST_DATA)
    json_output = dt.generate_json(G)
    
    # Verify that the output is valid JSON
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        pytest.fail("Generated JSON is not valid")
    
    # Verify the structure of the JSON output
    assert isinstance(data, dict)
    assert "nodes" in data
    assert "edges" in data
    assert "directed" in data
    assert data["directed"] is True
    
    # Verify that all nodes and edges are present
    assert len(data["nodes"]) == G.number_of_nodes()
    assert len(data["edges"]) == G.number_of_edges()
    
    # Verify node format
    for node in data["nodes"]:
        assert "id" in node
        assert node["id"] in G.nodes
    
    # Verify edge format
    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert G.has_edge(edge["source"], edge["target"])