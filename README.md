# manipuPom

:warning: This utility has mostly been written with the Github Copilot, and I have only superficially checked its adequacy. Seems to be ok, but use at your own risk.

[![Lint and unit tests](https://github.com/hansi-b/manipuPom/actions/workflows/lint_and_unit_tests.yml/badge.svg)](https://github.com/hansi-b/manipuPom/actions/workflows/lint_and_unit_tests.yml)


Small utility to read and modify a Maven `pom.xml` using Python's
`xml.etree.ElementTree`. It can also visualize dependency relationships across multiple Maven projects.

This repository contains:

- `src/mod_deps.py` — Script to modify dependencies. It can remove
  dependencies by `artifactId`, change the scope of dependencies, and optionally write changes back to the
  POM file. When writing, the script will automatically create a
  `.bak` backup of the original file.
- `src/deps_tree.py` — Script to generate dependency graphs from Maven projects. It can analyze multiple
  POM files in a directory structure and output the dependency relationships in either PlantUML or JSON format.
- `src/mod_parent.py` — Script to update `<parent><version>` in multiple POM files. Works recursively and can
  update many POMs in place or perform a dry-run.
- `src/evaluate_mvn_builds.py` — Script to evaluate Maven build logs in a directory and produce a human-friendly report
  listing successful builds, failure groups, and unreadable/inconclusive logs.
- `tests/` — pytest-based unit tests.
- `tests/data/` — test data used by the test suite.
- `requirements.txt` — development/test dependencies (currently
  contains `pytest` and `networkx`).

## Features

### mod_deps.py

- Remove `<dependency>` entries by passing one or more `--delete artifactId`
  values on the command line.
- Change dependency `<scope>` using `--scope artifactId:newScope` format.
- Optionally overwrite the original POM; a `.bak` copy is always
  created before overwriting.

### deps_tree.py

- Generate dependency graphs from all POM files in a directory structure.
- Output dependency relationships in either PlantUML or JSON format.
- Visualize root projects and leaf dependencies in separate clusters.
- Identify and visualize project dependencies based on groupId:artifactId pairs.
- Filter dependencies by including or excluding specific groupIds.
- Flexible node naming with optional groupId inclusion.
- Support writing output to files or standard output.

### mod_parent.py

- Update `<parent><version>` entries across multiple POM files under a directory root.
- By default the script runs a dry-run and prints a summary; use `--write` to persist changes.
- Creates a backup of the original file when writing; backup file is named `pom.xml.bak` (for input `pom.xml`).
- Namespace-aware: handles POMs with a default namespace on the `<project>` element.

### evaluate_mvn_builds.py

- Evaluate Maven build logs inside a directory (wildcard `*.log`) and produce a detailed human-friendly report.
- Reads logs in binary mode and decodes lines using UTF-8; lines that cannot be decoded are skipped.
- Groups failures by category (e.g., "Dependency Resolution", "Compilation Failure") and includes the filenames for each group.
- Lists successful builds (filenames) and reports unreadable / inconclusive logs.
- Optional `--outfile` flag writes the report to a file instead of printing to stdout.
- Includes the final consecutive ERROR lines (if present) for each non-successful log in the report so you can quickly inspect the failure context.

## Requirements

- Python 3.10+
- modules as listed in `requirements.txt`

## Installation / Setup

Recommended: create and activate a virtual environment, then install
requirements:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

From the repository root you can run the script directly. The CLI
signature is:

```
python3 src/mod_deps.py <pom-path> [--delete ARTIFACT ...] [--write] [--scope ARTIFACT:SCOPE ...]
```

Examples:

- Remove dependencies by `artifactId` and print the modified POM:

```bash
python3 src/mod_deps.py someProject/pom.xml --delete htmlcleaner jxl
```

- Remove dependencies and overwrite the POM (a `.bak` copy will be
  created automatically):

```bash
python3 src/mod_deps.py someProject/pom.xml --delete htmlcleaner jxl --write
```

- Change dependency scopes (can be combined with removal):

```bash
python3 src/mod_deps.py someProject/pom.xml --scope junit:test lombok:provided
```

To generate a dependency graph:

```bash
# Generate PlantUML output (default)
python3 src/deps_tree.py path/to/maven/project

# Generate JSON output
python3 src/deps_tree.py path/to/maven/project --format json

# Write output to a file
python3 src/deps_tree.py path/to/maven/project --format plantuml --outfile deps.puml

# Show artifactIds with group IDs
python3 src/deps_tree.py path/to/maven/project --add-group-id

# Only include specific groups
python3 src/deps_tree.py path/to/maven/project --include-groups org.springframework com.example

# Exclude specific groups
python3 src/deps_tree.py path/to/maven/project --exclude-groups org.apache.logging org.slf4j

# Combine options
python3 src/deps_tree.py path/to/maven/project --add-group-id --include-groups org.springframework --format json
```

To update parent versions across a directory of POMs:

```bash
# Dry-run (default) - show which POMs would be updated
python3 src/mod_parent.py path/to/maven/root 3.2.0

# Write changes and create backups
python3 src/mod_parent.py path/to/maven/root 3.2.0 --write

```

Filter updates by parent artifactIds (comma-separated):

```
# Only update POMs whose <parent><artifactId> is one of 'company-parent' or 'platform-parent'
python3 src/mod_parent.py path/to/maven/root 3.2.0 --matching-parents company-parent,platform-parent

# Combine with --write to persist changes
python3 src/mod_parent.py path/to/maven/root 3.2.0 --write --matching-parents company-parent,platform-parent
```

Notes:
- The `--matching-parents` flag performs exact string matching on `<parent><artifactId>` values.
- Whitespace around commas is trimmed (e.g. `a-parent, b-parent` works).
- If provided, only POMs whose parent artifactId is in the set are considered; others are skipped silently.

To evaluate Maven build logs and produce a detailed report:

```bash
# Basic report to stdout
python3 src/evaluate_mvn_builds.py path/to/log/dir

# Write report to a file
python3 src/evaluate_mvn_builds.py path/to/log/dir --outfile mvn-report.txt

# Write JSON report to a file
python3 src/evaluate_mvn_builds.py path/to/log/dir --format json --outfile mvn-report.json
```

Notes about behavior
- The script uses namespace-aware matching. It detects the default
  namespace from the root tag so it will match `artifactId` elements
  that live in the same namespace.
- Matching of `artifactId` is exact. If you want case-insensitive or
  substring matching, the script can be extended with flags to alter
  matching behavior.
- The `.bak` backup is created at `<pom-path>.bak`. If a `.bak` file
  already exists it will be overwritten.

## Tests

Tests are provided using `pytest` in `tests`. Run tests with a venv Python (example):

```bash
python -m pytest -q
```

Or with an activated venv that has `pytest` installed:

```bash
pytest -q
```
