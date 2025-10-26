from pathlib import Path


import sys
import json
from pathlib import Path
from pom_utils import get_qn_lambda, iter_deps, read_pom
import xml.etree.ElementTree as ET

def find_poms_in_dir(dir_path: Path) -> list[Path]:
    """Find all pom.xml files under the given directory using pathlib.rglob."""
    root = Path(dir_path)
    return sorted(root.rglob('pom.xml'))

def extract_dependencies(pom_path: Path) -> tuple[str, list[str]]:
    """Extract dependency artifactIds from a pom.xml file."""
    root = read_pom(str(pom_path))
    qn = get_qn_lambda(root)
    
    artifactId = root.find(qn('artifactId'))
    if artifactId is not None and artifactId.text:
        artifact_name = artifactId.text
    else:
        print(f"Error: No <artifactId> found in {pom_path}", file=sys.stderr)
        sys.exit(1)

    dependency_ids = set()
    for dep in iter_deps(root):
        art = dep.find(qn('artifactId'))
        group = dep.find(qn('groupId'))
        if group is not None and group.text and art is not None and art.text:
            dependency_ids.add(f"{group.text}:{art.text}")
    print(f"Extracted {pom_path}: {dependency_ids}")
    return artifact_name, dependency_ids

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate dependency relations from all pom.xml files in a directory.")
    parser.add_argument("directory", help="Root directory to search for pom.xml files")
    args = parser.parse_args()

    pom_paths = find_poms_in_dir(args.directory)
    result = {}
    for pom_path in pom_paths:
        artifact, deps = extract_dependencies(pom_path)
        result[artifact] = sorted(deps)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
