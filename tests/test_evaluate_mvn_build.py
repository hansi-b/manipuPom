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
    # Verify that the report lists the successful filename and the failure filename
    assert "Successful build files:" in report
    assert "- success.log" in report
    assert "Compilation Failure: 1" in report
    assert "- failure.log" in report


def test_write_report_to_file(tmp_path):
    # Create a simple success log
    (tmp_path / 'ok.log').write_text("BUILD SUCCESS\n")

    report = ev.evaluate_build_logs(tmp_path)
    outfile = tmp_path / 'report.txt'
    # Use the helper function to write the report
    ev.write_report_to_file(report, outfile)
    assert outfile.exists()
    content = outfile.read_text(encoding='utf-8')
    assert "Successful Builds" in content


def test_evaluate_build_logs_json_data(tmp_path):
    # Create success and failure logs as before
    (tmp_path / 'success.log').write_text("BUILD SUCCESS\n")
    failure_log = tmp_path / 'failure.log'
    with open(failure_log, 'wb') as f:
        f.write(b"BUILD FAILURE\n")
        f.write(b"Compilation failure: details here\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    assert isinstance(data, dict)
    assert data['total_evaluated'] == 2
    assert data['failure_count'] == 1
    assert 'Compilation Failure' in data['failure_files_by_type']
    assert 'failure.log' in data['failure_files_by_type']['Compilation Failure']


def test_generate_json_report_and_write(tmp_path):
    (tmp_path / 'ok.log').write_text("BUILD SUCCESS\n")
    data = ev.evaluate_build_logs_data(tmp_path)
    json_report = ev.generate_json_report(data, pretty=True)
    # Validate JSON parsing
    import json as _json
    parsed = _json.loads(json_report)
    assert parsed['success_files'] == ['ok.log']
    outfile = tmp_path / 'report.json'
    ev.write_report_to_file(json_report, outfile)
    assert outfile.exists()
    content = outfile.read_text(encoding='utf-8')
    parsed2 = _json.loads(content)
    assert parsed2['success_files'] == ['ok.log']


def test_final_error_block_is_captured(tmp_path):
    # Create a failure log with multiple ERROR blocks; only the last consecutive block should be captured
    fail_log = tmp_path / 'fail.log'
    with open(fail_log, 'wb') as f:
        f.write(b"Some info\n")
        f.write(b"[ERROR] First error\n")
        f.write(b"Info line\n")
        f.write(b"[ERROR] Last error 1\n")
        f.write(b"[ERROR] Last error 2\n")
        f.write(b"BUILD FAILURE\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    assert 'fail.log' in data['failure_files_by_type'].get('Other Errors', []) or 'fail.log' in sum(data['failure_files_by_type'].values(), [])
    # The error block should be captured for this file
    assert 'fail.log' in data['error_blocks']
    assert data['error_blocks']['fail.log'] == ['[ERROR] Last error 1', '[ERROR] Last error 2']

    # Also check textual report includes the final error block lines
    report = ev.evaluate_build_logs(tmp_path)
    assert 'Final ERROR block:' in report
    assert 'Last error 1' in report
    assert 'Last error 2' in report


def test_trim_stop_message_removed_from_error_block(tmp_path):
    fail_log = tmp_path / 'stopfail.log'
    with open(fail_log, 'wb') as f:
        f.write(b"[ERROR] Something 1\n")
        f.write(b"[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.\n")
        f.write(b"[ERROR] stacktrace line 1\n")
        f.write(b"BUILD FAILURE\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    # The error block should be trimmed to only include lines before the stop message
    assert 'stopfail.log' in data['error_blocks']
    assert data['error_blocks']['stopfail.log'] == ['[ERROR] Something 1']
    # Text report should not include the stop message or stacktrace lines
    txt = ev.evaluate_build_logs(tmp_path)
    assert 'To see the full stack trace' not in txt
    assert 'stacktrace line 1' not in txt


def test_trim_help_message_removed_from_error_block(tmp_path):
    fail_log = tmp_path / 'helpfail.log'
    with open(fail_log, 'wb') as f:
        f.write(b"[ERROR] Something else\n")
        f.write(b"[ERROR] -> [Help 1]\n")
        f.write(b"[ERROR] trailing detail\n")
        f.write(b"BUILD FAILURE\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    assert 'helpfail.log' in data['error_blocks']
    assert data['error_blocks']['helpfail.log'] == ['[ERROR] Something else']
    txt = ev.evaluate_build_logs(tmp_path)
    assert '-> [Help 1]' not in txt
    assert 'trailing detail' not in txt


def test_error_block_strips_timestamps(tmp_path):
    # Log lines with leading timestamps before [ERROR]
    log = tmp_path / 'tsfail.log'
    with open(log, 'wb') as f:
        f.write(b"20:52:13,597 [ERROR] Timestamped error line 1\n")
        f.write(b"20:52:13,600 [ERROR] Timestamped error line 2\n")
        f.write(b"BUILD FAILURE\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    assert 'tsfail.log' in data['error_blocks']
    # Timestamps should be stripped
    assert data['error_blocks']['tsfail.log'] == ['[ERROR] Timestamped error line 1', '[ERROR] Timestamped error line 2']
    txt = ev.evaluate_build_logs(tmp_path)
    assert '[ERROR] Timestamped error line 1' in txt
    assert '20:52:13,597 [ERROR]' not in txt

def test_error_block_strips_date_and_timestamp(tmp_path):
    log = tmp_path / 'datedfail.log'
    with open(log, 'wb') as f:
        f.write(b"2025-11-27 20:52:13,597 [ERROR] Date stamped error line A\n")
        f.write(b"2025-11-27T20:52:14,001 [ERROR] DateT stamped error line B\n")
        f.write(b"BUILD FAILURE\n")

    data = ev.evaluate_build_logs_data(tmp_path)
    assert 'datedfail.log' in data['error_blocks']
    assert data['error_blocks']['datedfail.log'] == [
        '[ERROR] Date stamped error line A',
        '[ERROR] DateT stamped error line B'
    ]
    txt = ev.evaluate_build_logs(tmp_path)
    assert 'Date stamped error line A' in txt
    assert '2025-11-27 20:52:13,597 [ERROR]' not in txt
    assert '2025-11-27T20:52:14,001 [ERROR]' not in txt
