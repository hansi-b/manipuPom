import sys
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

# Ensure src is on sys.path so we can import mod_deps
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import mod_deps as md
from pom_utils import get_default_namespace

TEST_POM = Path(__file__).resolve().parent / 'data' / 'pom.xml'

def test_change_dependency_version_update_and_insert(tmp_path):
    """Change existing version and insert a missing one."""
    tmp_pom = tmp_path / 'pom.xml'
    shutil.copy2(TEST_POM, tmp_pom)
    root = md.read_pom(str(tmp_pom))

    ns = get_default_namespace(root)
    qn = lambda local: f"{{{ns}}}{local}" if ns else local

    # Remove the <version> element from one dependency to test insertion
    removed_for_artifact = 'testng'
    for dep in root.findall('.//' + qn('dependency')):
        art = dep.find(qn('artifactId'))
        if art is not None and art.text == removed_for_artifact:
            ver = dep.find(qn('version'))
            if ver is not None:
                dep.remove(ver)
            break

    # Ensure it's removed
    testng_dep = None
    for dep in root.findall('.//' + qn('dependency')):
        art = dep.find(qn('artifactId'))
        if art is not None and art.text == removed_for_artifact:
            testng_dep = dep
            break
    assert testng_dep is not None
    assert testng_dep.find(qn('version')) is None

    # Prepare changes: one existing (htmlcleaner) and one missing (testng)
    version_changes = ["htmlcleaner:2.22", "testng:7.11.0"]
    modified = md.apply_deps_changes(root, 'version',version_changes)

    assert modified == 2

    # Verify updates
    for dep in root.findall('.//' + qn('dependency')):
        art = dep.find(qn('artifactId'))
        ver = dep.find(qn('version'))
        if art is None:
            continue
        if art.text == 'htmlcleaner':
            assert ver is not None and ver.text == '2.22'
        elif art.text == 'testng':
            assert ver is not None and ver.text == '7.11.0'
