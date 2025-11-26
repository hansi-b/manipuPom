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
    Evaluate Maven build logs in the given directory and return a summary report.
    
    This function reads logs in binary mode and decodes them line-by-line using UTF-8.
    Lines that cannot be decoded due to encoding errors are skipped; this allows parsing
    logs produced in mixed encodings without failing with UnicodeDecodeError.
    """
    success_count = 0
    failure_count = 0
    error_types: dict[str, int] = {}

    for log_file in sorted(log_dir.glob('*.log')):
        print(f"Reading {log_file}...")
        detected_success = False
        detected_failure = False
        # Classification flags for this file
        file_error_class = None
        # Read the file in binary mode and decode line-by-line; skip lines that fail to decode
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
                if not file_error_class and "Could not resolve dependencies" in line:
                    file_error_class = "Dependency Resolution"
                elif not file_error_class and "Compilation failure" in line:
                    file_error_class = "Compilation Failure"
                # keep scanning; we only need to know if success/failure occurred somewhere
        if detected_success:
            success_count += 1
        elif detected_failure:
            failure_count += 1
            if file_error_class:
                error_types[file_error_class] = error_types.get(file_error_class, 0) + 1
            else:
                error_types["Other Errors"] = error_types.get("Other Errors", 0) + 1

    report_lines = [
        f"Total Builds Evaluated: {success_count + failure_count}",
        f"Successful Builds: {success_count}",
        f"Failed Builds: {failure_count}",
        "Error Classification:"
    ]
    for error_type, count in error_types.items():
        report_lines.append(f"  {error_type}: {count}")

    return "\n".join(report_lines)

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate Maven build logs in a directory.")
    p.add_argument("log_dir", help="Directory containing Maven build log files")
    return p.parse_args(argv)

if __name__ == "__main__":

    args = parse_args(sys.argv[1:])
    log_dir = Path(args.log_dir)
    if not log_dir.exists() or not log_dir.is_dir():
        print(f"Error: log directory does not exist or is not a directory: {log_dir}", file=sys.stderr)
        sys.exit(1)

    report = evaluate_build_logs(log_dir)
    print(report)
