import os
import sys
from pathlib import Path
import json
import pytest

# Ensure src is on sys.path so we can import deps_graph
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import deps_graph as dt
import networkx as nx

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

def test_build_graph_without_group_ids():
    """Test building graph with groupIds excluded from node names"""
    G = dt.build_dependency_graph(TEST_DATA, include_group_id=False)
    
    # Verify that no node names contain colons (which would indicate groupId:artifactId format)
    for node in G.nodes:
        assert ':' not in node

def test_graph_with_included_groups():
    """Test building graph with only specific included groups"""
    # First get a normal graph to find a group to include
    full_G = dt.build_dependency_graph(TEST_DATA)
    # Get the first group we find
    sample_group = next(node.split(':')[0] for node in full_G.nodes if ':' in node)
    
    # Now build a graph with only this group
    G = dt.build_dependency_graph(TEST_DATA, included_groups={sample_group})
    
    # Verify that all nodes either have the included group or don't have a group specified
    for node in G.nodes:
        if ':' in node:  # If node has a group specified
            group = node.split(':')[0]
            assert group == sample_group

def test_graph_with_excluded_groups():
    """Test building graph with specific excluded groups"""
    # First get a normal graph to find a group to exclude
    full_G = dt.build_dependency_graph(TEST_DATA)
    # Get the first group we find
    excluded_group = next(node.split(':')[0] for node in full_G.nodes if ':' in node)
    
    # Now build a graph excluding this group
    G = dt.build_dependency_graph(TEST_DATA, excluded_groups={excluded_group})
    
    # Verify that no nodes have the excluded group
    for node in G.nodes:
        if ':' in node:  # If node has a group specified
            group = node.split(':')[0]
            assert group != excluded_group

def test_graph_with_include_exclude_interaction():
    """Test that exclude groups takes precedence over include groups"""
    # First get a normal graph to find groups to include and exclude
    full_G = dt.build_dependency_graph(TEST_DATA)
    groups = {node.split(':')[0] for node in full_G.nodes if ':' in node}
    if len(groups) >= 2:
        group_list = list(groups)
        included_group = group_list[0]
        excluded_group = group_list[0]  # Use same group to test exclusion precedence
        
        G = dt.build_dependency_graph(TEST_DATA, 
                                    included_groups={included_group},
                                    excluded_groups={excluded_group})
        
        # Verify that nodes with the excluded group are not present, even though
        # the group was also in the included_groups
        for node in G.nodes:
            if ':' in node:
                group = node.split(':')[0]
                assert group != excluded_group

def test_extract_dependencies_filtered_root():
    """Test that filtering applies to root project as well"""
    # Get a sample pom path
    pom_path = dt.find_poms_in_dir(TEST_DATA)[0]
    
    # Get the normal output first to find the root's group
    root_artifact, _ = dt.extract_dependencies(pom_path)
    if ':' in root_artifact:
        root_group = root_artifact.split(':')[0]
        
        # Now exclude the root's group
        filtered_result = dt.extract_dependencies(pom_path, excluded_groups={root_group})
        
        # Should return None for filtered root
        assert filtered_result[0] is None
        assert len(filtered_result[1]) == 0

def test_get_transitive_dependencies():
    """Test transitive dependencies resolution."""
    G = dt.build_dependency_graph(TEST_DATA)
    # pick a module that has at least one outgoing edge
    module = next((n for n in G.nodes if G.out_degree(n) > 0), None)
    assert module is not None

    deps = set(dt.get_transitive_dependencies(G, module))
    expected = nx.descendants(G, module)
    assert deps == expected

def test_get_transitive_dependencies_missing():
    """Missing module should return empty list."""
    G = dt.build_dependency_graph(TEST_DATA)
    assert dt.get_transitive_dependencies(G, 'nonexistent:module') == []

def test_get_transitive_dependents():
    """Test transitive dependents resolution."""
    G = dt.build_dependency_graph(TEST_DATA)
    # pick a module that has at least one incoming edge
    module = next((n for n in G.nodes if G.in_degree(n) > 0), None)
    assert module is not None

    deps = set(dt.get_transitive_dependents(G, module))
    expected = nx.ancestors(G, module)
    assert deps == expected

def _flatten_tree(tree: dict) -> set:
    """Helper to collect all nodes from nested tree dict."""
    nodes = set()
    if not tree:
        return nodes
    def rec(d):
        for k, v in d.items():
            nodes.add(k)
            if isinstance(v, dict):
                rec(v)
    rec(tree)
    return nodes

def _build_parent_map(tree: dict, root: str = None) -> dict:
    """Return mapping child->parent from nested tree structure.
    
    Args:
        tree: The tree dict
        root: The root node (parent of top-level keys). If None, top-level keys have no parent in the map.
    """
    parent = {}
    def rec(node, subtree):
        for child, sub in subtree.items():
            parent[child] = node
            if isinstance(sub, dict):
                rec(child, sub)
    
    # If root is provided, top-level keys are children of root
    # Otherwise, they're orphans (parent is not tracked)
    if root is not None:
        for top_level_child, subtree in tree.items():
            parent[top_level_child] = root
            if isinstance(subtree, dict):
                rec(top_level_child, subtree)
    else:
        for top_level_child, subtree in tree.items():
            if isinstance(subtree, dict):
                rec(top_level_child, subtree)
    
    return parent

def test_transitive_dependencies_tree_structure():
    G = dt.build_dependency_graph(TEST_DATA)
    module = next((n for n in G.nodes if G.out_degree(n) > 0), None)
    assert module is not None

    tree = dt.get_transitive_dependencies_tree(G, module)
    assert isinstance(tree, dict)
    # flattened nodes should match descendants
    flat = _flatten_tree(tree)
    assert flat == nx.descendants(G, module)

    # verify parent-child in tree corresponds to shortest path predecessor
    parent_map = _build_parent_map(tree, module)
    paths = nx.single_source_shortest_path(G, module)
    for node in flat:
        path = paths[node]
        expected_parent = path[-2]
        assert parent_map[node] == expected_parent

def test_transitive_dependents_tree_structure():
    G = dt.build_dependency_graph(TEST_DATA)
    module = next((n for n in G.nodes if G.in_degree(n) > 0), None)
    assert module is not None

    tree = dt.get_transitive_dependents_tree(G, module)
    assert isinstance(tree, dict)
    flat = _flatten_tree(tree)
    assert flat == nx.ancestors(G, module)

    parent_map = _build_parent_map(tree, module)
    RG = G.reverse(copy=True)
    paths = nx.single_source_shortest_path(RG, module)
    for node in flat:
        path = paths[node]
        expected_parent = path[-2]
        assert parent_map[node] == expected_parent

def test_get_transitive_dependents_missing():
    """Missing module should return empty list for dependents."""
    G = dt.build_dependency_graph(TEST_DATA)
    assert dt.get_transitive_dependents(G, 'nonexistent:module') == []

def test_get_module_roots():
    """Test getting module roots from a dependency graph"""
    # Build a simple test graph
    G = dt.build_dependency_graph(TEST_DATA)
    
    # Get module roots
    roots = dt.get_filtered_nodes(G, lambda n: G.in_degree(n) == 0)
    
    # Verify that roots is a list
    assert isinstance(roots, list)
    
    # Verify that roots are sorted
    assert roots == sorted(roots)
    
    # Verify that all items in roots are nodes in the graph
    for root in roots:
        assert root in G.nodes
    
    # Verify that all roots have no incoming edges
    for root in roots:
        assert G.in_degree(root) == 0
    
    # Verify that there is at least one root
    assert len(roots) > 0

def test_get_module_roots_empty_graph():
    """Test getting module roots from an empty graph"""
    G = dt.build_dependency_graph(Path(__file__).resolve().parent / 'nonexistent')
    roots = dt.get_filtered_nodes(G, lambda n: G.in_degree(n) == 0)

    # Empty graph should have no roots
    assert roots == []

def test_get_module_roots_with_filtering():
    """Test getting module roots with group filtering applied"""
    # Build graph with group IDs included
    G = dt.build_dependency_graph(TEST_DATA, include_group_id=True)
    roots = dt.get_filtered_nodes(G, lambda n: G.in_degree(n) == 0)
    
    # Verify roots are properly identified even with groupIds
    for root in roots:
        assert G.in_degree(root) == 0
    
    # Should still have at least one root
    assert len(roots) > 0

def test_get_module_leaves():
    """Test getting module leaves from a dependency graph"""
    # Build a simple test graph
    G = dt.build_dependency_graph(TEST_DATA)
    
    # Get module leaves
    leaves = dt.get_filtered_nodes(G, lambda n: G.out_degree(n) == 0)
    
    # Verify that leaves is a list
    assert isinstance(leaves, list)
    
    # Verify that leaves are sorted
    assert leaves == sorted(leaves)
    
    # Verify that all items in leaves are nodes in the graph
    for leaf in leaves:
        assert leaf in G.nodes
    
    # Verify that all leaves have no outgoing edges
    for leaf in leaves:
        assert G.out_degree(leaf) == 0
    
    # Verify that there is at least one leaf
    assert len(leaves) > 0

def test_get_module_leaves_empty_graph():
    """Test getting module leaves from an empty graph"""
    G = dt.build_dependency_graph(Path(__file__).resolve().parent / 'nonexistent')
    leaves = dt.get_filtered_nodes(G, lambda n: G.out_degree(n) == 0)
    
    # Empty graph should have no leaves
    assert leaves == []

def test_get_module_leaves_with_filtering():
    """Test getting module leaves with group filtering applied"""
    # Build graph with group IDs included
    G = dt.build_dependency_graph(TEST_DATA, include_group_id=True)
    leaves = dt.get_filtered_nodes(G, lambda n: G.out_degree(n) == 0)
    
    # Verify leaves are properly identified even with groupIds
    for leaf in leaves:
        assert G.out_degree(leaf) == 0
    
    # Should still have at least one leaf
    assert len(leaves) > 0