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
from pom_utils import get_default_namespace, iter_deps_with_container


TEST_POM = Path(__file__).resolve().parent / 'data' / 'pom.xml'


def test_get_default_namespace_and_root_tag():
    root = md.read_pom(str(TEST_POM))
    ns = get_default_namespace(root)
    assert ns == 'http://maven.apache.org/POM/4.0.0'
    # root tag should include the namespace when parsed by ElementTree
    assert root.tag.startswith('{') and 'http://maven.apache.org/POM/4.0.0' in root.tag

def test_iter_deps_with_container():
    root = md.read_pom(str(TEST_POM))
    ns = get_default_namespace(root)
    qn = lambda local: f"{{{ns}}}{local}" if ns else local

    found_containers = set()
    found_deps = set()
    for container, deps in iter_deps_with_container(root):
        found_containers.add(container.tag)
        for dep in deps:
            art = dep.find(qn('artifactId'))
            if art is not None:
                found_deps.add(art.text)

    assert qn('dependencies') in found_containers
    expected_deps = {"test-deps-graph-a", "test-deps-graph-b", "htmlcleaner", "selenium-java", "testng", "jxl"}
    assert found_deps == expected_deps
