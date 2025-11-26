"""
Read all the maven build log files from the argument directory and sort them according to
build success and error.
Classify the errors into different categories and print a summary report.
"""
import sys
from pathlib import Path
import argparse

def evaluate_build_logs(log_dir: Path) -> str:
    """
    Evaluate Maven build logs in the given directory and return a detailed summary report.

    - Reads logs in binary mode and decodes them line-by-line using UTF-8.
      Lines that cannot be decoded due to encoding errors are skipped.
    - Returns a report listing each successful log and grouped failures with file names.
    """
    success_files: list[str] = []
    failure_files_by_type: dict[str, list[str]] = {}
    failure_count = 0
    unreadable_files: list[str] = []

    for log_file in sorted(log_dir.glob('*.log')):
        print(f"Reading {log_file}...")
        detected_success = False
        detected_failure = False
        # Classification flags for this file
        file_error_class = None
        # Read the file in binary mode and decode line-by-line; skip lines that fail to decode
        try:
            with open(log_file, 'rb') as f:
                for byte_line in f:
                    try:
                        line = byte_line.decode('utf-8')
                    except UnicodeDecodeError:
                        # Skip this line if it contains undecodable bytes
                        continue
                    if "BUILD SUCCESS" in line:
                        detected_success = True
                    if "BUILD FAILURE" in line:
                        detected_failure = True
                    if (not file_error_class) and "Could not resolve dependencies" in line:
                        file_error_class = "Dependency Resolution"
                    elif (not file_error_class) and "Compilation failure" in line:
                        file_error_class = "Compilation Failure"
                    # keep scanning; we only need to know if success/failure occurred somewhere
        except Exception:
            # If the file cannot be opened or read, list it as unreadable and continue
            unreadable_files.append(log_file.name)
            continue

        if detected_success:
            success_files.append(log_file.name)
        elif detected_failure:
            failure_count += 1
            group_key = file_error_class or "Other Errors"
            failure_files_by_type.setdefault(group_key, []).append(log_file.name)
        else:
            # If neither marker is present, consider the log unreadable or inconclusive
            unreadable_files.append(log_file.name)

    total_evaluated = len(success_files) + failure_count
    report_lines = [
        f"Total Builds Evaluated: {total_evaluated}",
        f"Successful Builds: {len(success_files)}",
    ]
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
    else:
        report_lines.append("  (no failures found)")

    if unreadable_files:
        report_lines.append("Unreadable / Inconclusive logs:")
        for fn in unreadable_files:
            report_lines.append(f"  - {fn}")

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

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate Maven build logs in a directory.")
    p.add_argument("log_dir", help="Directory containing Maven build log files")
    p.add_argument("--outfile", "-o", help="Write the generated report to this file (optional)")
    return p.parse_args(argv)

if __name__ == "__main__":

    args = parse_args(sys.argv[1:])
    log_dir = Path(args.log_dir)
    if not log_dir.exists() or not log_dir.is_dir():
        print(f"Error: log directory does not exist or is not a directory: {log_dir}", file=sys.stderr)
        sys.exit(1)

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
