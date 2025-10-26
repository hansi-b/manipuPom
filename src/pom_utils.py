import sys
import xml.etree.ElementTree as ET
from typing import Iterable, Optional

def get_default_namespace(elem: ET.Element) -> Optional[str]:
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
    ns = get_default_namespace(root)
    return (lambda local: f"{{{ns}}}{local}") if ns else lambda local: local


def read_pom(pom_path):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    return root


def iter_deps_with_container(root: ET.Element):
    """
    Generator that yields (dependencies_container, list_of_dependency_elements) tuples."""
    qn = get_qn_lambda(root)
    for deps_container in root.findall('.//' + qn('dependencies')):
        yield deps_container, deps_container.findall(qn('dependency'))

def iter_deps(root: ET.Element):
    """
    Generator that yields dependency elements."""
    deps_with_container = iter_deps_with_container(root)
    for _, deps in deps_with_container:
        for dep in deps:
            yield dep

def find_artifactids(root: ET.Element) -> set:
    """Return a set of dependency artifactId text values found in the POM (namespace-aware).
    """
    qn = get_qn_lambda(root)
    artifact_ids = set()
    for dep in iter_deps(root):
        art = dep.find(qn('artifactId'))
        if art is not None and art.text:
            artifact_ids.add(art.text)
    return artifact_ids

def verify_artifactids_arguments(pom_root: ET.Element, requested: Iterable[str]):
    """
    Verify that all requested artifactIds are present in the POM.
    If any are missing, print an error and exit.
    """
    present = find_artifactids(pom_root)
    missing = requested - present
    if missing:
        print(f"Error: specified artifactIds not found in POM: {', '.join(sorted(missing))}", file=sys.stderr)
        # Do not modify or write anything if a requested dependency is missing
        sys.exit(1)
