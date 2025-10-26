from pathlib import Path


# Generate a graph representation of the dependencies of a list of POM files.


def find_poms_in_dir(dir_path: Path) -> list[Path]:
    """Find all pom.xml files under the given directory using pathlib.rglob.

    Returns a list of Path objects. The list is sorted to provide a stable
    ordering for tests.
    """
    root = Path(dir_path)
    # rglob yields Paths in arbitrary order depending on filesystem; sort for stability
    poms = sorted(root.rglob('pom.xml'))
    return poms

if __name__ == '__main__':
    pass