from pathlib import Path
import sys


import networkx as nx

from pom_utils import get_qn_lambda, iter_deps, read_pom


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

def write_json(G: nx.DiGraph, output_file: str|None):
    """Generate a JSON representation of the dependency graph."""
    data = nx.readwrite.json_graph.node_link_data(G, edges="edges")
    import json
    if output_file is None:
        print(json.dumps(data, indent=2))
        return
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Dependency graph written to {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate dependency relations graph from all pom.xml files in a directory.")
    parser.add_argument("directory", help="Root directory to search for pom.xml files")
    parser.add_argument("--outfile", "-f", help="If provided, save JSON to this file.")
    args = parser.parse_args()

    # Build graph and visualize
    G = build_dependency_graph(Path(args.directory))
    print(f"Built dependency graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    # write the graph as JSON
    write_json(G, args.outfile)
    

if __name__ == "__main__":
    main()
