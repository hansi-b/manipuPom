import sys
import subprocess
from pathlib import Path

# Ensure src is on sys.path so we can import mod_deps
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import xml.etree.ElementTree as ET
import shutil

import pytest

import mod_deps as md


TEST_POM = Path(__file__).resolve().parent / 'data' / 'pom.xml'


def test_get_default_namespace_and_root_tag():
    root = md.read_pom(str(TEST_POM))
    ns = md._get_default_namespace(root)
    assert ns == 'http://maven.apache.org/POM/4.0.0'
    # root tag should include the namespace when parsed by ElementTree
    assert root.tag.startswith('{') and 'http://maven.apache.org/POM/4.0.0' in root.tag


def test_remove_dependencies_removes_by_artifactid(tmp_path):
    # copy the data pom to a temporary file so tests don't mutate repo files
    tmp_pom = tmp_path / 'pom.xml'
    shutil.copy2(TEST_POM, tmp_pom)

    root = md.read_pom(str(tmp_pom))

    # ensure the artifactIds we will remove are present initially
    artifact_ids = {"htmlcleaner", "jxl"}
    found = set()
    ns = md._get_default_namespace(root)
    qn = lambda local: f"{{{ns}}}{local}" if ns else local
    for art in root.findall('.//' + qn('artifactId')):
        if art.text in artifact_ids:
            found.add(art.text)
    assert found == artifact_ids

    removed = md.remove_dependencies(root, artifact_ids)
    assert removed == 2

    # after removal, there should be no artifactId elements with those texts
    remaining = [art.text for art in root.findall('.//' + qn('artifactId')) if art.text in artifact_ids]
    assert remaining == []


def test_change_dependency_scopes(tmp_path):
    """Test changing and adding dependency scopes"""
    # copy the data pom to a temporary file so tests don't mutate repo files
    tmp_pom = tmp_path / 'pom.xml'
    shutil.copy2(TEST_POM, tmp_pom)

    root = md.read_pom(str(tmp_pom))
    ns = md._get_default_namespace(root)
    qn = lambda local: f"{{{ns}}}{local}" if ns else local

    # Test both changing an existing scope and adding a new one
    scope_changes = ["testng:test", "selenium-java:provided"]
    modified = md.change_dependency_scopes(root, scope_changes)
    assert modified == 2

    # Verify the changes
    for deps_container in root.findall('.//' + qn('dependencies')):
        for dep in deps_container.findall(qn('dependency')):
            art = dep.find(qn('artifactId'))
            scope = dep.find(qn('scope'))
            if art.text == 'testng':
                assert scope is not None and scope.text == 'test'
            elif art.text == 'selenium-java':
                assert scope is not None and scope.text == 'provided'

def test_script_fails_on_missing_dependency(tmp_path, capsys):
    """Verify the script fails with exit code 1 when a requested artifactId doesn't exist."""
    # copy test POM to a temporary location so we don't modify the original
    tmp_pom = tmp_path / 'pom.xml'
    shutil.copy2(TEST_POM, tmp_pom)

    # Invoke the module's main() with arguments and expect SystemExit(1)
    argv = [str(tmp_pom), '--delete', 'non-existent-artifact']
    with pytest.raises(SystemExit) as excinfo:
        md.main(argv)
    # SystemExit code should be 1
    assert excinfo.value.code == 1
    # Capture printed stderr output and ensure error message is present
    captured = capsys.readouterr()
    assert "Error: specified artifactIds not found in POM: non-existent-artifact" in captured.err

    # The POM should not be modified (content should match original)
    with open(TEST_POM) as f:
        original = f.read()
    with open(tmp_pom) as f:
        modified = f.read()
    assert modified == original