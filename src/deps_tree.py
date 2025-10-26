import os
from pathlib import Path

# Generate a graph representation of the dependencies of a list of POM files.


def find_poms_under(dir_path: Path) -> set[Path]:
    """find all pom under the argument directory
    """
    return { Path(root) / f for root, dirs, files in os.walk(dir_path) for f in files if f == 'pom.xml' }

if __name__ == '__main__':
    pass