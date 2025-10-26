import os
import sys
from pathlib import Path

# Ensure src is on sys.path so we can import deps_tree
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import deps_tree as dt

TEST_DATA = Path(__file__).resolve().parent / 'data'

def test_find_poms_in_dir():
    """Test finding POMs in a directory structure"""
    # Get all POMs
    poms = dt.find_poms_in_dir(TEST_DATA)
    
    # Should find exactly 3 POMs - one in data dir, one in repo_a, one in repo_b
    assert len(poms) == 3
    
    # Verify all found paths exist and are actually pom.xml files
    for pom in poms:
        assert pom.exists()
        assert pom.name == 'pom.xml'
    
    # Verify we found the specific expected POMs
    expected_poms = {
        TEST_DATA / 'pom.xml',
        TEST_DATA / 'repo_a' / 'pom.xml',
        TEST_DATA / 'repo_b' / 'pom.xml'
    }
    assert set(poms) == expected_poms

def test_find_poms_in_empty_dir(tmp_path):
    """Test finding POMs in an empty directory"""
    poms = dt.find_poms_in_dir(tmp_path)
    assert len(poms) == 0

def test_find_poms_in_dir_with_no_poms(tmp_path):
    """Test finding POMs in a directory that has files but no POMs"""
    # Create some non-POM files
    (tmp_path / 'file1.txt').touch()
    (tmp_path / 'file2.xml').touch()
    os.mkdir(tmp_path / 'subdir')
    (tmp_path / 'subdir' / 'other.xml').touch()
    
    poms = dt.find_poms_in_dir(tmp_path)
    assert len(poms) == 0