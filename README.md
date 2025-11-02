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
