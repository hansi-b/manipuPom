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
    old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")
    assert old_version == "1.0.0"
    assert "<version>2.0.0</version>" in xml_text
    # Should not modify if already up to date
    pom_path.write_text(make_pom_with_parent("2.0.0"))
    old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")
    assert old_version == "2.0.0"
    assert xml_text is None

def test_update_parent_version_in_pom_with_namespace(tmp_path):
    ns = "http://maven.apache.org/POM/4.0.0"
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text(make_pom_with_parent("1.0.0", ns=ns))
    old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "3.1.4")
    assert old_version == "1.0.0"
    assert "<version>3.1.4</version>" in xml_text

def test_update_parent_version_in_pom_no_parent(tmp_path):
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text("""<project><artifactId>child</artifactId></project>""")
    old_version, xml_text = mod_parent.update_parent_version_in_pom(pom_path, "2.0.0")
    assert old_version is None
    assert xml_text is None

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

def test_process_poms_under_with_parent_artifact_filter(tmp_path):
    # Two POMs with different parent artifactIds
    pom1 = tmp_path / "x" / "pom.xml"
    pom1.parent.mkdir(parents=True)
    pom1.write_text(make_pom_with_parent("1.0.0"))  # parent-artifact

    pom2 = tmp_path / "y" / "pom.xml"
    pom2.parent.mkdir(parents=True)
    pom2.write_text(
        """<project>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>another-parent</artifactId>
    <version>5.0.0</version>
  </parent>
  <artifactId>child2</artifactId>
</project>"""
    )

    # Only update those with matching parent artifactId
    changed = mod_parent.process_poms_under(tmp_path, "9.9.9", write=False, parent_artifact_ids={"parent-artifact"})
    assert len(changed) == 1
    assert changed[0][0] == pom1
    assert changed[0][1] == "1.0.0"
    assert changed[0][2] == "9.9.9"

    # Using non-matching filter updates none
    changed_none = mod_parent.process_poms_under(tmp_path, "7.7.7", write=False, parent_artifact_ids={"nonexistent-parent"})
    assert changed_none == []

def test_process_poms_under_with_multiple_matching_parents(tmp_path):
    # Three POMs with two different parent artifactIds
    pom_a = tmp_path / "a" / "pom.xml"
    pom_a.parent.mkdir(parents=True)
    pom_a.write_text(make_pom_with_parent("1.0.0"))  # parent-artifact

    pom_b = tmp_path / "b" / "pom.xml"
    pom_b.parent.mkdir(parents=True)
    pom_b.write_text(
        """<project>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>another-parent</artifactId>
    <version>2.0.0</version>
  </parent>
  <artifactId>childB</artifactId>
</project>"""
    )

    pom_c = tmp_path / "c" / "pom.xml"
    pom_c.parent.mkdir(parents=True)
    pom_c.write_text(
        """<project>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>third-parent</artifactId>
    <version>3.0.0</version>
  </parent>
  <artifactId>childC</artifactId>
</project>"""
    )

    # Match first two parents only
    changed = mod_parent.process_poms_under(tmp_path, "9.9.9", write=False, parent_artifact_ids={"parent-artifact", "another-parent"})
    # Order of traversal deterministic via sorted rglob; ensure both updated
    changed_paths = {c[0] for c in changed}
    assert pom_a in changed_paths and pom_b in changed_paths and pom_c not in changed_paths
    # Ensure version mapping correct
    for path, old_ver, new_ver in changed:
        assert new_ver == "9.9.9"
