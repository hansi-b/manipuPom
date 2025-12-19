import sys
from pathlib import Path

import networkx as nx

# Ensure src is on sys.path so we can import deps_graph
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import deps_graph as dt


def _test_data_dir() -> Path:
    here = Path(__file__).parent
    return here / "data"


def _build_graph() -> nx.DiGraph:
    return dt.build_dependency_graph(_test_data_dir(), include_group_id=True)


def test_minimal_subgraph_direct_edge_between_repo_a_and_b():
    G = _build_graph()
    a = "example.org:test-deps-graph-a"
    b = "example.org:test-deps-graph-b"

    H = dt.minimal_subgraph_for_artifacts(G, [a, b])

    assert set(H.nodes) >= {a, b}
    # a depends on b directly; inverted edge is b -> a
    assert H.has_edge(b, a)
    # No original direction edge
    assert not H.has_edge(a, b)


def test_minimal_subgraph_repo_a_to_htmlcleaner():
    G = _build_graph()
    a = "example.org:test-deps-graph-a"
    html = "net.sourceforge.htmlcleaner:htmlcleaner"

    H = dt.minimal_subgraph_for_artifacts(G, [a, html])

    assert set(H.nodes) >= {a, html}
    # a depends on htmlcleaner; inverted edge is html -> a
    assert H.has_edge(html, a)


def test_minimal_subgraph_no_connection_between_two_leaves():
    G = _build_graph()
    html = "net.sourceforge.htmlcleaner:htmlcleaner"
    testng = "org.testng:testng"

    H = dt.minimal_subgraph_for_artifacts(G, [html, testng])

    # both present, but no path between them in dependency direction
    assert html in H.nodes
    assert testng in H.nodes
    assert H.number_of_edges() == 0
