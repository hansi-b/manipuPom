"""
Read all the maven build log files from the argument directory and sort them according to
build success and error.
Classify the errors into different categories and print a summary report.
"""
import sys
from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone


def _trim_error_block(block: list[str]) -> list[str]:
    """Trim any lines starting from the stack-trace hint line in an error block.

    Remove the line containing the Maven stack trace hint ("To see the full stack trace") and any
    subsequent lines.
    """
    if not block:
        return block
    stop_msg = "[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch."
    help_msg = "[ERROR] -> [Help 1]"
    for idx, l in enumerate(block):
        if stop_msg in l or help_msg in l:
            return block[:idx]
    return block


def _process_log_file(log_file: Path) -> dict:
    """Process a single log file and return its detection/classification data.

    Returns a dict with keys:
      - filename: str
      - detected_success: bool
      - detected_failure: bool
      - file_error_class: str | None
      - last_error_block: list[str] (trimmed)
      - unreadable: bool
    """
    # Initialize
    detected_success = False
    detected_failure = False
    file_error_class = None
    last_error_block: list[str] = []
    current_error_block: list[str] = []
    unreadable = False
    finished_at: str | None = None

    try:
        with open(log_file, 'rb') as f:
            for byte_line in f:
                try:
                    line = byte_line.decode('utf-8')
                except UnicodeDecodeError:
                    continue
                if "BUILD SUCCESS" in line:
                    detected_success = True
                if "BUILD FAILURE" in line:
                    detected_failure = True
                if (not file_error_class) and "Could not resolve dependencies" in line:
                    file_error_class = "Dependency Resolution"
                elif (not file_error_class) and "Compilation failure" in line:
                    file_error_class = "Compilation Failure"
                # Capture 'Finished at:' timestamp
                if 'Finished at:' in line:
                    try:
                        raw = line.split('Finished at:', 1)[1].strip()
                        token = raw.split()[0]
                        try:
                            dt = datetime.fromisoformat(token)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            finished_at = dt.isoformat()
                        except Exception:
                            finished_at = token
                    except Exception:
                        pass
                if ('[ERROR]' in line) or line.lstrip().startswith('ERROR'):
                    cleaned = line.strip()
                    # Remove leading timestamp pattern (HH:MM:SS,mmm) directly preceding an [ERROR] tag
                    # Strip leading timestamp patterns optionally including a date:
                    # Examples removed:
                    #   20:52:13,597 [ERROR] ...
                    #   2025-11-27 20:52:13,597 [ERROR] ...
                    #   2025-11-27T20:52:13,597 [ERROR] ...
                    cleaned = re.sub(r'^(?:\d{4}-\d{2}-\d{2}[ T])?\d{2}:\d{2}:\d{2}[.,]\d{3}\s+(?=\[ERROR])', '', cleaned)
                    current_error_block.append(cleaned)
                else:
                    if current_error_block:
                        last_error_block = current_error_block
                        current_error_block = []
    except Exception:
        unreadable = True

    if current_error_block:
        last_error_block = current_error_block

    return {
        'filename': log_file.name,
        'detected_success': detected_success,
        'detected_failure': detected_failure,
        'file_error_class': file_error_class,
        'last_error_block': _trim_error_block(last_error_block) if last_error_block else [],
        'unreadable': unreadable,
        'finished_at': finished_at,
    }

def evaluate_build_logs_data(log_dir: Path) -> dict:
    """Return structured data about build log evaluation.

    This returns a dict with keys: 'total_evaluated', 'success_files',
    'failure_count', 'failure_files_by_type', 'unreadable_files'.
    """
    success_files: list[str] = []
    failure_files_by_type: dict[str, list[str]] = {}
    failure_count = 0
    unreadable_files: list[str] = []
    error_blocks: dict[str, list[str]] = {}
    finished_timestamps: list[datetime] = []
    finished_raw: list[str] = []

    for log_file in sorted(log_dir.glob('*.log')):
        print(f"Reading {log_file}...")
        entry = _process_log_file(log_file)
        if entry['unreadable']:
            unreadable_files.append(entry['filename'])
            if entry['last_error_block']:
                error_blocks[entry['filename']] = entry['last_error_block']
            if entry.get('finished_at'):
                try:
                    dt = datetime.fromisoformat(entry['finished_at'])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    finished_timestamps.append(dt)
                    finished_raw.append(entry['finished_at'])
                except Exception:
                    finished_raw.append(entry['finished_at'])
            continue
        if entry['detected_success']:
            success_files.append(entry['filename'])
        elif entry['detected_failure']:
            failure_count += 1
            group_key = entry['file_error_class'] or "Other Errors"
            failure_files_by_type.setdefault(group_key, []).append(entry['filename'])
            if entry['last_error_block']:
                error_blocks[entry['filename']] = entry['last_error_block']
        else:
            unreadable_files.append(entry['filename'])
            if entry['last_error_block']:
                error_blocks[entry['filename']] = entry['last_error_block']

        # Collect finished_at timestamps if present (for success/failure and other cases)
        if entry.get('finished_at'):
            try:
                dt = datetime.fromisoformat(entry['finished_at'])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                finished_timestamps.append(dt)
                finished_raw.append(entry['finished_at'])
            except Exception:
                finished_raw.append(entry['finished_at'])

    total_evaluated = len(success_files) + failure_count
    # Derived counts for JSON consumers
    failure_type_counts = {k: len(v) for k, v in failure_files_by_type.items()}
    # Place counts first to appear at the beginning of JSON output
    # Determine first and last Finished at timestamps if available
    first_finished_at = None
    last_finished_at = None
    if finished_timestamps:
        first_finished_at = min(finished_timestamps).isoformat()
        last_finished_at = max(finished_timestamps).isoformat()
    elif finished_raw:
        first_finished_at = min(finished_raw)
        last_finished_at = max(finished_raw)
    return {
        'first_finished_at': first_finished_at,
        'last_finished_at': last_finished_at,
        'total_evaluated': total_evaluated,
        'success_count': len(success_files),
        'failure_count': failure_count,
        'unreadable_count': len(unreadable_files),
        'failure_type_counts': failure_type_counts,
        'success_files': success_files,
        'failure_files_by_type': failure_files_by_type,
        'unreadable_files': unreadable_files,
        'error_blocks': error_blocks,
    }


def evaluate_build_logs(log_dir: Path) -> str:
    """
    Evaluate Maven build logs in the given directory and return a detailed summary report.

    - Reads logs in binary mode and decodes them line-by-line using UTF-8.
      Lines that cannot be decoded due to encoding errors are skipped.
    - Returns a report listing each successful log and grouped failures with file names.
    """
    data = evaluate_build_logs_data(log_dir)
    success_files = data['success_files']
    failure_files_by_type = data['failure_files_by_type']
    failure_count = data['failure_count']
    unreadable_files = data['unreadable_files']
    total_evaluated = data['total_evaluated']
    # Header summary with totals and per-type failure counts
    first_finished_at = data.get('first_finished_at') or 'N/A'
    last_finished_at = data.get('last_finished_at') or 'N/A'
    # Put the finished at range first in the report
    finished_range_line = f"Finished at range: {first_finished_at} -> {last_finished_at}"
    summary_line = (
        f"Total Builds Evaluated: {total_evaluated} | Successes: {len(success_files)} | "
        f"Failures: {failure_count} | Unreadable/Inconclusive: {len(unreadable_files)}"
    )
    report_lines = [finished_range_line, summary_line]
    if failure_files_by_type:
        # Compose concise failure type counts line
        type_counts = ", ".join([f"{t}: {len(fs)}" for t, fs in failure_files_by_type.items()])
        report_lines.append(f"Failure Types: {type_counts}")
    if unreadable_files:
        # Compact list of unreadable/inconclusive files
        compact_unreadable = ", ".join(sorted(unreadable_files))
        report_lines.append(f"Unreadable/Inconclusive files: {compact_unreadable}")
    # Preserve existing detailed sections for backward compatibility
    report_lines.append(f"Successful Builds: {len(success_files)}")
    if success_files:
        report_lines.append("Successful build files:")
        for s in success_files:
            report_lines.append(f"  - {s}")
    report_lines.append(f"Failed Builds: {failure_count}")
    report_lines.append("Failure Classification:")
    if failure_files_by_type:
        for error_type, files in failure_files_by_type.items():
            report_lines.append(f"  {error_type}: {len(files)}")
            for fn in files:
                report_lines.append(f"    - {fn}")
                # Include a final ERROR block for each failure file if available
                err_block = data.get('error_blocks', {}).get(fn)
                if err_block:
                    report_lines.append("      Final ERROR block:")
                    for bl in err_block:
                        report_lines.append(f"        {bl}")
    else:
        report_lines.append("  (no failures found)")

    if unreadable_files:
        report_lines.append("Unreadable / Inconclusive logs:")
        for fn in unreadable_files:
            report_lines.append(f"  - {fn}")
            # Also include final ERROR block if present
            err_block = data.get('error_blocks', {}).get(fn)
            if err_block:
                report_lines.append("    Final ERROR block:")
                for bl in err_block:
                    report_lines.append(f"      {bl}")

    return "\n".join(report_lines)


def write_report_to_file(report: str, outfile: Path) -> None:
    """Write the given report to the provided outfile path using UTF-8 encoding.

    Creating parent directories if necessary and overwriting any existing file.
    """
    outfile_path = Path(outfile)
    if not outfile_path.parent.exists():
        outfile_path.parent.mkdir(parents=True, exist_ok=True)
    with open(outfile_path, 'w', encoding='utf-8') as f:
        f.write(report)


def generate_json_report(data: dict, pretty: bool = True) -> str:
    """Serialize the evaluation data to JSON.

    - If pretty is True, the output is indented for readability.
    """
    if pretty:
        return json.dumps(data, indent=2)
    return json.dumps(data)

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate Maven build logs in a directory.")
    p.add_argument("log_dir", help="Directory containing Maven build log files")
    p.add_argument("--outfile", "-o", help="Write the generated report to this file (optional)")
    p.add_argument("--format", "-f", choices=["text", "json"], default="text",
                   help="Output format for the report (text or json); default: text")
    args = p.parse_args(argv)

    # Helper: detect an explicit --format or -f value in argv and return it
    def _explicit_format_value(argv_list: list[str]) -> str | None:
        for idx, val in enumerate(argv_list):
            if val == '-f' or val == '--format':
                # value should be the next arg, if present
                if idx + 1 < len(argv_list):
                    return argv_list[idx + 1]
                return None
            if val.startswith('--format='):
                return val.split('=', 1)[1]
            if val.startswith('-f') and len(val) > 2:
                # forms like -fjson or -ftext
                return val[2:]
        return None

    explicit_fmt = _explicit_format_value(argv)
    outfile = getattr(args, 'outfile', None)
    if outfile and str(outfile).lower().endswith('.json'):
        if explicit_fmt and explicit_fmt.lower() == 'text':
            # Error: explicit text format and json outfile conflict
            print("Error: requested text output (\"--format text\") conflicts with outfile name ending in '.json'", file=sys.stderr)
            raise SystemExit(1)
        # If no explicit format or explicit is json (or unspecified), prefer JSON
        args.format = 'json'

    return args

if __name__ == "__main__":

    args = parse_args(sys.argv[1:])
    log_dir = Path(args.log_dir)
    if not log_dir.exists() or not log_dir.is_dir():
        print(f"Error: log directory does not exist or is not a directory: {log_dir}", file=sys.stderr)
        sys.exit(1)

    if getattr(args, 'format', 'text') == 'json':
        data = evaluate_build_logs_data(log_dir)
        report = generate_json_report(data, pretty=True)
    else:
        report = evaluate_build_logs(log_dir)

    if getattr(args, 'outfile', None):
        try:
            write_report_to_file(report, Path(args.outfile))
            print(f"Wrote report to {args.outfile}")
        except Exception as e:
            print(f"Error writing report to {args.outfile}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(report)
