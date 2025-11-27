"""Modify parent version across multiple Maven POMs.

Find all pom.xml files under a given root directory and, when a <parent>
section is present, replace its <version> value with the user-specified
version.

Behavior:
 - By default (no --write) shows a summary of intended changes without
   modifying files.
 - With --write, each modified pom.xml is overwritten after creating a
   .bak backup copy.
 - Only POMs that actually contain a <parent><version>...</version></parent>
   element are considered for modification.

Namespace handling:
Maven POMs usually declare a default namespace on the root <project> element.
ElementTree represents namespaced tags with '{uri}local'. We retrieve the
namespace (if any) and qualify child lookup accordingly so both namespaced
and non-namespaced POMs are supported uniformly.
"""

from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from typing import Iterable

from pom_utils import get_default_namespace, get_qn_lambda, read_pom


def find_poms(root: Path) -> list[Path]:
    """Return all pom.xml paths under root (recursive)."""
    return sorted(root.rglob("pom.xml"))


def update_parent_version_in_pom(pom_path: Path, new_version: str, parent_artifact_ids: set[str] | None = None) -> tuple[str | None, str | None]:
    """Update the parent version in a single pom.xml file.

    Returns (old_version, xml_text) where:
        old_version: previous version string (None if no parent/version found)
        xml_text: the updated XML as string ready to be written, or None if not modified
    """
    root = read_pom(str(pom_path))
    qn = get_qn_lambda(root)

    parent_elem = root.find(qn("parent"))
    if parent_elem is None:
        return None, None
    # If a filter for parent artifactId is provided, ensure it matches
    if parent_artifact_ids is not None:
        art_elem = parent_elem.find(qn("artifactId"))
        if art_elem is None or art_elem.text is None or art_elem.text.strip() not in parent_artifact_ids:
            return None, None
    ver_elem = parent_elem.find(qn("version"))
    if ver_elem is None or ver_elem.text is None:
        return None, None

    old_version = ver_elem.text.strip()
    if old_version == new_version:
        return old_version, None

    # Register namespace (if any) for clean writing
    ns = get_default_namespace(root)
    if ns:
        ET.register_namespace('', ns)

    ver_elem.text = new_version
    # Produce updated XML text for writing by caller
    xml_text = ET.tostring(root, encoding='unicode')
    return old_version, xml_text


def process_poms_under(root_dir: Path, new_version: str, write: bool, parent_artifact_ids: set[str] | None = None) -> list[tuple[Path, str, str]]:
    """Scan all pom.xml under root_dir, updating parent version.

    Returns a list of tuples (pom_path, old_version, new_version) for changed files.
    """
    changed: list[tuple[Path, str, str]] = []
    for pom in find_poms(root_dir):
        # Use the helper function to update and obtain results
        try:
            old_version, xml_text = update_parent_version_in_pom(pom, new_version, parent_artifact_ids)
        except Exception as e:  # pragma: no cover - robust to parse errors
            print(f"Warning: Failed to parse {pom}: {e}", file=sys.stderr)
            continue

        if xml_text is None:
            continue

        # Optionally write back to disk
        if write:
            import shutil
            backup = pom.with_suffix('.xml.bak')
            shutil.copy2(pom, backup)
            with open(pom, 'w', encoding='utf-8') as f:
                f.write(xml_text)

        changed.append((pom, old_version, new_version))
    return changed


def parse_args(argv: Iterable[str] | None = None):
    import argparse
    p = argparse.ArgumentParser(description="Update parent version across multiple pom.xml files under a root directory.")
    p.add_argument("root", help="Root directory to search recursively for pom.xml files")
    p.add_argument("version", help="New parent version to set")
    p.add_argument("--write", "-w", action="store_true", help="Persist changes (otherwise show a dry-run summary)")
    p.add_argument("--matching-parents", dest="matching_parents", help="Comma-separated list of parent artifactIds to match (exact). Only matching parents are updated.", default=None)
    return p.parse_args(argv)


def main(argv: Iterable[str] | None = None):
    args = parse_args(argv)
    root_dir = Path(args.root)
    if not root_dir.exists():
        print(f"Error: root directory does not exist: {root_dir}", file=sys.stderr)
        sys.exit(1)

    parent_ids: set[str] | None
    if args.matching_parents:
        parent_ids = {p.strip() for p in args.matching_parents.split(',') if p.strip()}
    else:
        parent_ids = None
    changed = process_poms_under(root_dir, args.version, args.write, parent_ids)
    if not changed:
        print("No parent versions needed updating.")
        return

    if args.write:
        print(f"Updated parent version to {args.version} in {len(changed)} POM(s):")
        for pom, old_ver, new_ver in changed:
            print(f"  {pom} : {old_ver} -> {new_ver}")
    else:
        print(f"Dry-run: would update parent version to {args.version} in {len(changed)} POM(s):")
        for pom, old_ver, new_ver in changed:
            print(f"  {pom} : {old_ver} -> {new_ver}")


if __name__ == "__main__":
    main()