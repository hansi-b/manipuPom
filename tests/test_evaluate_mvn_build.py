import sys
from pathlib import Path
import pytest

# Ensure src on sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import evaluate_mvn_build as ev


def test_evaluate_build_logs_with_undecodable_lines(tmp_path):
    """Test that lines with undecodable bytes are skipped and evaluation continues."""
    # Create success log (valid utf-8)
    success_log = tmp_path / 'success.log'
    success_log.write_text("Some build output\nBUILD SUCCESS\n")

    # Create failure log with an undecodable line and a compilation failure line
    failure_log = tmp_path / 'failure.log'
    # Write binary data to include invalid UTF-8 bytes
    with open(failure_log, 'wb') as f:
        f.write(b"Some initial log line\n")
        # Include an undecodable byte sequence (invalid in UTF-8)
        f.write(b"Invalid: \xa7\xff\x80\n")
        f.write(b"BUILD FAILURE\n")
        f.write(b"Compilation failure: details here\n")

    report = ev.evaluate_build_logs(tmp_path)
    # Report should include 2 total builds, 1 success, 1 failure
    assert "Total Builds Evaluated: 2" in report
    assert "Successful Builds: 1" in report
    assert "Failed Builds: 1" in report
    # Should classify the failure as Compilation Failure
    assert "Compilation Failure: 1" in report
