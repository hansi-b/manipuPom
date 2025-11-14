# read argument pom.xml and parse as xml

import sys
import xml.etree.ElementTree as ET
from typing import Iterable
from pom_utils import get_default_namespace, get_qn_lambda, iter_deps, iter_deps_with_container, verify_deps_arguments, read_pom


def remove_dependencies(root: ET.Element, requested: Iterable[str]):
    """
    Remove <dependency> elements whose <artifactId> text is in artifact_names.
    """
    verify_deps_arguments(root, requested)

    qn = get_qn_lambda(root)

    removed = 0
    for deps_container, deps in iter_deps_with_container(root):
        # iterate over a copy since we'll remove elements
        for dep in list(deps):
            art = dep.find(qn('artifactId'))
            if art is not None and art.text in requested:
                deps_container.remove(dep)
                removed += 1
    return removed


def parse_artifact_changes(changes: Iterable[str]) -> dict[str, str]:
    """
    Parse changes from 'artifactId:new_value' strings into a dictionary.
    """
    changes_map = {}
    for change in changes:
        try:
            artifact_id, new_scope = change.split(':')
            changes_map[artifact_id] = new_scope
        except ValueError:
            print(f"Error: Invalid change format '{change}'. Expected 'artifactId:new_value'", file=sys.stderr)
            sys.exit(1)
    return changes_map


def apply_deps_changes(root: ET.Element, target_element: str, changes: Iterable[str]) -> int:
    """
    Change or add given target elements in dependencies based on 'artifactId:new_value' pairs.
    Returns number of dependencies modified.
    """
    change_map = parse_artifact_changes(changes)
    verify_deps_arguments(root, set(change_map.keys()))

    modified = 0
    qn = get_qn_lambda(root)
    for dep in iter_deps(root):
        art = dep.find(qn('artifactId'))
        if art is not None and art.text in change_map:
            ver_elem = dep.find(qn(target_element))
            if ver_elem is None:
                # Create new target element if it doesn't exist
                ver_elem = ET.SubElement(dep, qn(target_element))
            ver_elem.text = change_map[art.text]
            modified += 1

    return modified


def parse_args(argv=None):
    import argparse
    p = argparse.ArgumentParser(description='Modify dependencies in a pom.xml')
    p.add_argument('pom', help='path to pom.xml (required positional)')
    p.add_argument('--delete', '-d', nargs='+', metavar='ARTIFACT',
                  help='artifactIds to remove from dependencies')
    p.add_argument('--write', '-w', action='store_true', help='overwrite the input pom with the modified XML (a .bak copy will be created)')
    p.add_argument('--scope', '-s', nargs='+', metavar='ARTIFACT:SCOPE',
                  help='change dependency scopes. Format: artifactId:newScope (e.g., junit:test)')
    p.add_argument('--version', '-v', nargs='+', metavar='ARTIFACT:VERSION',
                  help='change dependency versions. Format: artifactId:newVersion (e.g., junit:4.13.2)')
    return p.parse_args(argv)


def main(argv=None):
    """Main entry point. Accepts argv (list of strings) for programmatic invocation.

    When called directly from the command line __name__ == '__main__', pass None
    so argparse reads from sys.argv. For tests, pass an argv list.
    """
    args = parse_args(argv)
    pom_path = args.pom
    pom_root = read_pom(pom_path)

    if args.delete:
        removed = remove_dependencies(pom_root, set(args.delete))
        print(f"Removed {removed} matching dependencies", flush=True)

    if args.scope:
        modified = apply_deps_changes(pom_root, 'scope', args.scope)
        print(f"Modified {modified} dependency scopes", flush=True)

    if args.version:
        modified = apply_deps_changes(pom_root, 'version', args.version)
        print(f"Modified {modified} dependency versions", flush=True)

    # Register the root's namespace as the default namespace so ElementTree
    # writes a single xmlns="..." on the root instead of repeated xmlns:prefix
    # declarations on many elements. This preserves namespace semantics while
    # avoiding prefixes on element tags.
    ns = get_default_namespace(pom_root)
    if ns:
        ET.register_namespace('', ns)

    out = ET.tostring(pom_root, encoding='unicode')

    if args.write:
        import shutil
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

if __name__ == "__main__":
    main()
