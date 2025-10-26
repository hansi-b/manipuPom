# read argument pom.xml and parse as xml
import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from typing import Iterable


def read_pom(pom_path):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    return root


def _get_default_namespace(elem):
    """
    If the element tag uses a namespace (e.g. '{uri}local'), return the URI.
    Otherwise return None.
    """
    tag = elem.tag
    if isinstance(tag, str) and tag.startswith('{') and '}' in tag:
        return tag[1:tag.index('}')]
    return None


def get_qn_lambda(root: ET.Element):
    """
    Returns a lambda that generates qualified names for the given XML root's namespace.
    """
    ns = _get_default_namespace(root)
    return (lambda local: f"{{{ns}}}{local}") if ns else lambda local: local


def handle_remove_deps(pom_root: ET.Element, requested: Iterable[str]):
    """
    If artifacts to remove were passed, verify they're present then remove matching dependencies
    """
    present = find_artifactids(pom_root)
    missing = requested - present
    if missing:
        print(f"Error: specified artifactIds not found in POM: {', '.join(sorted(missing))}", file=sys.stderr)
        # Do not modify or write anything if a requested dependency is missing
        sys.exit(1)

    removed = remove_dependencies(pom_root, requested)
    print(f"Removed {removed} matching dependencies", flush=True)

def remove_dependencies(root: ET.Element, artifact_names: Iterable[str]) -> int:
    """
    Remove <dependency> elements whose <artifactId> text is in artifact_names.

    Returns number of removed dependencies.
    """
    removed = 0
    qn = get_qn_lambda(root)

    # Find all <dependencies> containers and inspect their <dependency> children
    for deps_container in root.findall('.//' + qn('dependencies')):
        # iterate over a copy since we'll remove elements
        for dep in list(deps_container.findall(qn('dependency'))):
            art = dep.find(qn('artifactId'))
            if art is not None and art.text in artifact_names:
                deps_container.remove(dep)
                removed += 1
    return removed


def find_artifactids(root: ET.Element) -> set:
    """Return a set of artifactId text values found in the POM (namespace-aware)."""
    qn = get_qn_lambda(root)
    return {el.text for el in root.findall('.//' + qn('artifactId')) if el.text}


def change_dependency_scopes(root: ET.Element, scope_changes: Iterable[str]) -> int:
    """
    Change or add <scope> elements in dependencies based on 'artifactId:scope' pairs.
    Returns number of dependencies modified.
    """
    modified = 0
    qn = get_qn_lambda(root)

    # Parse the scope changes into a dict
    scope_map = {}
    for change in scope_changes:
        try:
            artifact_id, new_scope = change.split(':')
            scope_map[artifact_id] = new_scope
        except ValueError:
            print(f"Error: Invalid scope change format '{change}'. Expected 'artifactId:newScope'", file=sys.stderr)
            sys.exit(1)

    # Find all <dependencies> containers and inspect their <dependency> children
    for deps_container in root.findall('.//' + qn('dependencies')):
        for dep in deps_container.findall(qn('dependency')):
            art = dep.find(qn('artifactId'))
            if art is not None and art.text in scope_map:
                scope_elem = dep.find(qn('scope'))
                if scope_elem is None:
                    # Create new scope element if it doesn't exist
                    scope_elem = ET.SubElement(dep, qn('scope'))
                scope_elem.text = scope_map[art.text]
                modified += 1

    return modified


def parse_args():
    p = argparse.ArgumentParser(description='Modify dependencies in a pom.xml')
    p.add_argument('pom', help='path to pom.xml (required positional)')
    p.add_argument('--delete', '-d', nargs='+', metavar='ARTIFACT',
                  help='artifactIds to remove from dependencies')
    p.add_argument('--write', '-w', action='store_true', help='overwrite the input pom with the modified XML (a .bak copy will be created)')
    p.add_argument('--scope', '-s', nargs='+', metavar='ARTIFACT:SCOPE',
                  help='change dependency scopes. Format: artifactId:newScope (e.g., junit:test)')
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    pom_path = args.pom
    pom_root = read_pom(pom_path)

    if args.delete:
        handle_remove_deps(pom_root, set(args.delete))

    if args.scope:
        modified = change_dependency_scopes(pom_root, args.scope)
        print(f"Modified {modified} dependency scopes", flush=True)

    # Register the root's namespace as the default namespace so ElementTree
    # writes a single xmlns="..." on the root instead of repeated xmlns:prefix
    # declarations on many elements. This preserves namespace semantics while
    # avoiding prefixes on element tags.
    ns = _get_default_namespace(pom_root)
    if ns:
        ET.register_namespace('', ns)

    out = ET.tostring(pom_root, encoding='unicode')

    if args.write:
        # Always back up the original file before overwriting
        backup_path = f"{pom_path}.bak"
        shutil.copy2(pom_path, backup_path)
        print(f"Created backup: {backup_path}")

        # Overwrite the input file (UTF-8)
        with open(pom_path, 'w', encoding='utf-8') as f:
            f.write(out)
        print(f"Wrote modified POM to {pom_path}")
    else:
        print(out)
