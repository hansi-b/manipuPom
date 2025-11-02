from pathlib import Path
import sys


import networkx as nx

from pom_utils import get_qn_lambda, iter_deps, read_pom


def find_poms_in_dir(dir_path: Path) -> list[Path]:
    """Find all pom.xml files under the given directory using pathlib.rglob."""
    root = Path(dir_path)
    return sorted(root.rglob('pom.xml'))

def extract_dependencies(pom_path: Path, include_group_id: bool = False, included_groups: set[str] = None, excluded_groups: set[str] = None) -> tuple[str, list[str]]:
    """Extract dependency artifactIds from a pom.xml file.
    
    Args:
        pom_path: Path to the pom.xml file
        include_group_id: Whether to include groupId in artifact names
        included_groups: Set of group IDs to include (if None, include all)
        excluded_groups: Set of group IDs to exclude (if None, exclude none)
    """
    root = read_pom(str(pom_path))
    qn = get_qn_lambda(root)
    # Determine the root project's groupId:artifactId as the artifact key
    group_elem = root.find(qn('groupId'))
    artifact_elem = root.find(qn('artifactId'))
    
    if artifact_elem is not None and artifact_elem.text:
        if include_group_id and group_elem is not None and group_elem.text:
            artifact_name = f"{group_elem.text}:{artifact_elem.text}"
        else:
            artifact_name = artifact_elem.text
    else:
        print(f"Error: No <artifactId> found in {pom_path}", file=sys.stderr)
        sys.exit(1)
        
    # Filter out the root artifact if its group should be excluded
    if group_elem is not None and group_elem.text:
        group_id = group_elem.text
        if (included_groups and group_id not in included_groups) or \
           (excluded_groups and group_id in excluded_groups):
            return None, set()

    dependency_ids = set()
    for dep in iter_deps(root):
        art = dep.find(qn('artifactId'))
        group = dep.find(qn('groupId'))
        
        if art is not None and art.text:
            if group is not None and group.text:
                group_id = group.text
                # Filter dependencies based on group inclusion/exclusion
                if (included_groups and group_id not in included_groups) or \
                   (excluded_groups and group_id in excluded_groups):
                    continue
                    
                artifact_id = f"{group.text}:{art.text}" if include_group_id else art.text
            else:
                artifact_id = art.text
            dependency_ids.add(artifact_id)
            
    return artifact_name, dependency_ids


def build_dependency_graph(directory: Path, include_group_id: bool = True, included_groups: set[str] = None, excluded_groups: set[str] = None):
    """Build a directed NetworkX graph of dependencies for all POMs under directory.

    Args:
        directory: Root directory to search for pom.xml files
        include_group_id: Whether to include groupId in artifact names
        included_groups: Set of group IDs to include (if None, include all)
        excluded_groups: Set of group IDs to exclude (if None, exclude none)

    Returns:
        A NetworkX DiGraph where nodes are strings in the form 'groupId:artifactId' 
        when groupId is available and include_group_id is True, otherwise just the 
        artifactId. Edges point from a project to its declared dependencies.
    """
    G = nx.DiGraph()
    for pom_path in find_poms_in_dir(directory):
        artifact, deps = extract_dependencies(pom_path, 
                                           include_group_id=include_group_id,
                                           included_groups=included_groups,
                                           excluded_groups=excluded_groups)
        if artifact:  # Only add if the artifact wasn't filtered out
            G.add_node(artifact)
            for d in deps:
                G.add_node(d)
                G.add_edge(artifact, d)
    return G

def generate_plant_uml(G: nx.DiGraph) -> str:
    """Generate a PlantUML representation of the dependency graph."""
    
    # from the graph, find all nodes which have no incoming edges (i.e., root projects)
    roots = [n for n in G.nodes if G.in_degree(n) == 0]
    # from the graph, find all leaves (nodes with no outgoing edges)
    leaves = [n for n in G.nodes if G.out_degree(n) == 0]
    
    lines = ["@startuml", "digraph G {"]
    for node in G.nodes:
        lines.append(f'  "{node}" [shape=box, style=rounded]')
    
    # group the roots in a subgraph
    if roots:
        lines.append("  subgraph cluster_roots {")
        lines.append('    label="Root Projects";')
        for r in roots:
            lines.append(f'    "{r}";')
        lines.append("  }")
    # group the leaves in a subgraph
    if leaves:
        lines.append("  subgraph cluster_leaves {")
        lines.append('    label="Leaf Dependencies";')
        for l in leaves:
            lines.append(f'    "{l}";')
        lines.append("  }")
        
    for src, dst in G.edges:
        lines.append(f'  "{src}" -> "{dst}";')
    lines.append("}")
    lines.append("@enduml")
    return "\n".join(lines)

def generate_json(G: nx.DiGraph) -> str:   
    """Generate a JSON representation of the dependency graph."""
    import json
    data = nx.readwrite.json_graph.node_link_data(G, edges="edges")
    return json.dumps(data, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate dependency relations graph from all pom.xml files in a directory.")
    parser.add_argument("directory", help="Root directory to search for pom.xml files")
    parser.add_argument("--format", "-m", choices=["plantuml", "json"], default="plantuml",
                        help="Output format for the dependency graph (default: plantuml)")
    parser.add_argument("--outfile", "-f", help="If provided, write generated output to this file.")
    parser.add_argument("--add-group-id", action="store_true",
                        help="Include groupId in artifact names")
    parser.add_argument("--include-groups", nargs="+", metavar="GROUP_ID",
                        help="Only include artifacts from these groupIds. If not specified, include all groups.")
    parser.add_argument("--exclude-groups", nargs="+", metavar="GROUP_ID",
                        help="Exclude artifacts from these groupIds. Takes precedence over --include-groups.")
    args = parser.parse_args()

    # Convert groups to sets for efficient lookup
    included_groups = set(args.include_groups) if args.include_groups else None
    excluded_groups = set(args.exclude_groups) if args.exclude_groups else None

    # Build graph and visualize
    G = build_dependency_graph(Path(args.directory),
                             include_group_id=args.add_group_id,
                             included_groups=included_groups,
                             excluded_groups=excluded_groups)
    
    print(f"Built dependency graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    graph_output = ""
    if args.format == "plantuml":
        graph_output = generate_plant_uml(G)
    elif args.format == "json":
        graph_output = generate_json(G)
    if args.outfile:
        with open(args.outfile, "w") as f:
            f.write(graph_output)
        print(f"Wrote output to {args.outfile}")
    else:
        print(graph_output)

if __name__ == "__main__":
    main()
