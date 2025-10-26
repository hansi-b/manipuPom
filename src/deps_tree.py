from pathlib import Path


import sys
import json
from pathlib import Path

import matplotlib
from pom_utils import get_qn_lambda, iter_deps, read_pom
import xml.etree.ElementTree as ET
from typing import Optional


try:
    import networkx as nx
    import matplotlib.pyplot as plt
except Exception:
    nx = None
    plt = None
    raise RuntimeError("networkx and matplotlib are required to visualize graphs. Please install them.")

def find_poms_in_dir(dir_path: Path) -> list[Path]:
    """Find all pom.xml files under the given directory using pathlib.rglob."""
    root = Path(dir_path)
    return sorted(root.rglob('pom.xml'))

def extract_dependencies(pom_path: Path) -> tuple[str, list[str]]:
    """Extract dependency artifactIds from a pom.xml file."""
    root = read_pom(str(pom_path))
    qn = get_qn_lambda(root)
    # Determine the root project's groupId:artifactId as the artifact key
    group_elem = root.find(qn('groupId'))
    artifact_elem = root.find(qn('artifactId'))
    if artifact_elem is not None and artifact_elem.text:
        if group_elem is not None and group_elem.text:
            artifact_name = f"{group_elem.text}:{artifact_elem.text}"
        else:
            artifact_name = artifact_elem.text
    else:
        print(f"Error: No <artifactId> found in {pom_path}", file=sys.stderr)
        sys.exit(1)

    dependency_ids = set()
    for dep in iter_deps(root):
        art = dep.find(qn('artifactId'))
        group = dep.find(qn('groupId'))
        if group is not None and group.text and art is not None and art.text:
            dependency_ids.add(f"{group.text}:{art.text}")
    return artifact_name, dependency_ids


def build_dependency_graph(directory: Path):
    """Build a directed NetworkX graph of dependencies for all POMs under directory.

    Nodes are strings in the form 'groupId:artifactId' when groupId is available,
    otherwise just the artifactId. Edges point from a project to its declared
    dependencies.
    """

    G = nx.DiGraph()
    for pom_path in find_poms_in_dir(directory):
        artifact, deps = extract_dependencies(pom_path)
        G.add_node(artifact)
        for d in deps:
            G.add_node(d)
            G.add_edge(artifact, d)
    return G


def visualize_dependency_graph(G, figsize=(12, 8), output: Optional[str] = None):
    """Visualize dependency graph using matplotlib.

    If output is None, the plot is shown interactively. If output is a path,
    the image is saved to that path.
    """

    plt.figure(figsize=figsize)
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue')
    nx.draw_networkx_edges(G, pos, arrows=True)
    nx.draw_networkx_labels(G, pos, font_size=8)
    plt.axis('off')
    if output:
        plt.savefig(output, bbox_inches='tight')
        print(f"Saved dependency graph to {output}")
    else:
        plt.show()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Visualize dependency relations from all pom.xml files in a directory.")
    parser.add_argument("directory", help="Root directory to search for pom.xml files")
    parser.add_argument("--output", "-o", help="If provided, save visualization to this file (png/svg). Otherwise show interactively.")
    args = parser.parse_args()

    # Build graph and visualize
    G = build_dependency_graph(Path(args.directory))
    visualize_dependency_graph(G, output=args.output)

if __name__ == "__main__":
    main()
