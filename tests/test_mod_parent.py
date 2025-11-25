import tempfile
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import pytest
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent.parent / "src"))
import mod_parent

def make_pom_with_parent(version: str, ns: str = None) -> str:
    if ns:
        return f'''<project xmlns="{ns}">
  <parent>
    <groupId>com.example</groupId>
    <artifactId>parent-artifact</artifactId>
    <version>{version}</version>
  </parent>
  <artifactId>child</artifactId>
</project>'''
    else:
        return f'''<project>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>parent-artifact</artifactId>
    <version>{version}</version>
  </parent>
  <artifactId>child</artifactId>
</project>'''

def test_update_parent_version_in_pom(tmp_path):
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text(make_pom_with_parent("1.0.0"))
    modified, old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")
    assert modified is True
    assert old_version == "1.0.0"
    assert "<version>2.0.0</version>" in xml_text
    # Should not modify if already up to date
    pom_path.write_text(make_pom_with_parent("2.0.0"))
    modified, old_version = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")[:2]
    assert modified is False
    assert old_version == "2.0.0"

def test_update_parent_version_in_pom_with_namespace(tmp_path):
    ns = "http://maven.apache.org/POM/4.0.0"
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text(make_pom_with_parent("1.0.0", ns=ns))
    modified, old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "3.1.4")
    assert modified is True
    assert old_version == "1.0.0"
    assert "<version>3.1.4</version>" in xml_text

def test_update_parent_version_in_pom_no_parent(tmp_path):
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text("""<project><artifactId>child</artifactId></project>""")
    modified, old_version = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")[:2]
    assert modified is False
    assert old_version is None

def test_process_poms_under(tmp_path):
    # Create two POMs, one with parent, one without
    pom1 = tmp_path / "a" / "pom.xml"
    pom1.parent.mkdir(parents=True)
    pom1.write_text(make_pom_with_parent("1.0.0"))
    pom2 = tmp_path / "b" / "pom.xml"
    pom2.parent.mkdir(parents=True)
    pom2.write_text("""<project><artifactId>child</artifactId></project>""")
    changed = mod_parent.process_poms_under(tmp_path, "9.9.9", write=False)
    assert len(changed) == 1
    assert changed[0][0] == pom1
    assert changed[0][1] == "1.0.0"
    assert changed[0][2] == "9.9.9"
    # Test write mode creates backup
    changed = mod_parent.process_poms_under(tmp_path, "8.8.8", write=True)
    assert (pom1.parent / "pom.xml.bak").exists()
    # Confirm file updated
    tree = ET.parse(pom1)
    ver = tree.getroot().find(".//version")
    assert ver is not None and ver.text == "8.8.8"
