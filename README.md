# manipuPom

:warning: This utility has mostly been written with the Github Copilot, and I have only superficially checked its adequacy. Seems to be ok, but use at your own risk.

[![Lint and unit tests](https://github.com/hansi-b/manipuPom/actions/workflows/lint_and_unit_tests.yml/badge.svg)](https://github.com/hansi-b/manipuPom/actions/workflows/lint_and_unit_tests.yml)


A collection of small utilities around Maven:

- Read, analyse and modify one or more Maven `pom.xml` files.
- Read and summarise Maven build logs.

This repository contains:

- `src/mod_deps.py` — Script to modify dependencies. It can remove
  dependencies by `artifactId`, change the scope of dependencies, and optionally write changes back to the
  POM file. When writing, the script will automatically create a
  `.bak` backup of the original file.
- `src/mod_parent.py` — Script to update `<parent><version>` in multiple POM files. Works recursively and can
  update many POMs in place or perform a dry-run.
- `src/deps_graph.py` — Script to generate dependency graphs from Maven projects. It can analyse multiple
  POM files in a directory structure and output the dependency relationships in either PlantUML or JSON format.
- `src/evaluate_mvn_builds.py` — Script to evaluate Maven build logs in a directory and produce a human-friendly report
  listing successful builds, failure groups, and unreadable/inconclusive logs.
- `tests/` — pytest-based unit tests
- `tests/data/` — test data used by the test suite
- `requirements.txt` — development/test dependencies

## Features

### mod_deps.py

- Remove `<dependency>` entries by passing one or more `--delete artifactId`
  values on the command line.
- Change dependency `<scope>` using `--scope artifactId:newScope` format.
- Optionally overwrite the original POM; a `.bak` copy is always
  created before overwriting.

### deps_graph.py

- Generate dependency graphs from all POM files in a directory structure.
- Output dependency relationships in either PlantUML or JSON format.
- Visualize root projects and leaf dependencies in separate clusters.
- Identify and visualize project dependencies based on groupId:artifactId pairs.
- Filter dependencies by including or excluding specific groupIds.
- Flexible node naming with optional groupId inclusion.
- Support writing output to files or standard output.
 - CLI options to list module roots/leaves and show transitive dependency/dependent trees.
   - `--roots` / `--leaves`: print modules with no incoming / no outgoing edges.
   - `--dependencies MODULE` / `--dependents MODULE`: print transitive dependencies or dependents for `MODULE`.
    - PlantUML support: with `--format plantuml`, these modes render the corresponding tree as a directed graph suitable for PlantUML. The root `MODULE` is included, and edges follow the tree direction (dependencies: module → dependency; dependents: module → dependent).
  - Minimal subgraph for selected artifacts:
    - `--sub-graph A,B,C`: print the minimal subgraph containing the listed artifacts and intermediate connectors along the shortest directed dependency paths between them.
  - Mutually exclusive modes:
    - The options `--roots`, `--leaves`, `--dependencies`, `--dependents`, and `--sub-graph` are mutually exclusive. Specify at most one; if more than one is provided, the CLI will error and abort.
  - JSON output for roots/leaves:
    - When using `--roots` or `--leaves` with `--format json`, the script emits a flat JSON array of artifact node IDs.

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
- Shows a compact summary at the top: total evaluated, number of successes, failures, unreadable/inconclusive, and per-type failure counts.
- Includes the earliest and latest "Finished at:" timestamps found across all build logs, displayed at the top of the report, and returned in the JSON output as `first_finished_at` and `last_finished_at`.
- Strips leading timestamps (time-only or date+time) from error lines so `[ERROR]` lines are easier to read, e.g. `2025-11-27 20:52:13,597 [ERROR] ...` becomes `[ERROR] ...`.
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
python3 src/deps_graph.py path/to/maven/project

# Generate JSON output
python3 src/deps_graph.py path/to/maven/project --format json

# Write output to a file
python3 src/deps_graph.py path/to/maven/project --format plantuml --outfile deps.puml

# Show artifactIds with group IDs
python3 src/deps_graph.py path/to/maven/project --add-group-id

# Only include specific groups
python3 src/deps_graph.py path/to/maven/project --include-groups org.springframework com.example

# Exclude specific groups
python3 src/deps_graph.py path/to/maven/project --exclude-groups org.apache.logging org.slf4j

# Combine options
python3 src/deps_graph.py path/to/maven/project --add-group-id --include-groups org.springframework --format json

# Output only module roots (modules with no incoming edges)
python3 src/deps_graph.py path/to/maven/project --roots

# Output only module leaves (modules with no outgoing edges)
python3 src/deps_graph.py path/to/maven/project --leaves

# Show transitive dependencies of a module (use groupId:artifactId if --add-group-id was used)
python3 src/deps_graph.py path/to/maven/project --dependencies example.org:test-mod-deps

# Show transitive dependents (modules that (transitively) depend on MODULE)
python3 src/deps_graph.py path/to/maven/project --dependents org.seleniumhq.selenium:selenium-java

# Use flat output (newline list) instead of JSON tree
python3 src/deps_graph.py path/to/maven/project --dependencies example.org:test-mod-deps --flat
python3 src/deps_graph.py path/to/maven/project --dependents org.seleniumhq.selenium:selenium-java --flat

# Show all paths to each module, instead of just the first shortest path
python3 src/deps_graph.py path/to/maven/project --dependencies example.org:test-mod-deps --all-paths
python3 src/deps_graph.py path/to/maven/project --dependents org.seleniumhq.selenium:selenium-java --all-paths
```

##### Minimal Subgraph (`--sub-graph`)

The `--sub-graph` option builds a minimal subgraph that includes:
- All artifacts listed in the comma-separated argument.
- Any intermediate nodes that lie on the shortest directed dependency paths connecting those artifacts.
- Edges inverted relative to the full graph, so each edge points from dependency → dependent.

Examples:

```bash
# Minimal subgraph connecting two internal modules
python3 src/deps_graph.py path/to/maven/project --sub-graph example.org:test-deps-graph-a,example.org:test-deps-graph-b --format plantuml

# Minimal subgraph connecting a module to an external dependency, in JSON
python3 src/deps_graph.py path/to/maven/project --sub-graph example.org:test-deps-graph-a,net.sourceforge.htmlcleaner:htmlcleaner --format json

# Write the PlantUML subgraph to a file
python3 src/deps_graph.py path/to/maven/project --sub-graph A,B,C --format plantuml --outfile subgraph.puml
```

Notes:
- The subgraph only includes directed dependency chains (no upward “parent” connectors). If no path exists between a pair, those nodes remain in the subgraph without edges between them.
- Output supports both `plantuml` and `json` via `--format`.

#### Dependency Tree Output Format

When using `--dependencies` or `--dependents` without the `--flat` flag, the output is a JSON tree structure showing transitive relationships. By default, only the first shortest path to each module is included in the tree. The tree contains only the direct and transitive dependencies/dependents of the specified module (the argument module itself is not included in the tree).

For example, given a module `example.org:test-mod-deps` with transitive dependencies:
- `example.org:test-mod-deps` → `example.org:dep1` → `example.org:dep1-1`
- `example.org:test-mod-deps` → `example.org:dep2`

The output would be:
```json
{
  "example.org:dep1": {
    "example.org:dep1-1": {}
  },
  "example.org:dep2": {}
}
```

Note that the argument module (`example.org:test-mod-deps`) does not appear in the tree.

##### Using `--all-paths`

By default, the tree shows only the shortest path to each module. To include all paths to each module (useful for understanding all ways a dependency can be reached), use the `--all-paths` flag:

```bash
python3 src/deps_graph.py path/to/maven/project --dependencies example.org:test-mod-deps --all-paths
```

For example, if a module can be reached via multiple paths:
- `example.org:test-mod-deps` → `example.org:dep1` → `example.org:dep1-1`
- `example.org:test-mod-deps` → `example.org:dep2` → `example.org:dep1-1`

The output with `--all-paths` would be:
```json
{
  "example.org:dep1": {
    "example.org:dep1-1": {}
  },
  "example.org:dep2": {
    "example.org:dep1-1": {}
  }
}
```

Note that `example.org:dep1-1` now appears twice in the tree (under both `dep1` and `dep2`), showing all ways to reach that module.

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

Notes on `--format` and `--outfile`:
- If you pass an outfile name ending with `.json` and do not explicitly set `--format`, the script will automatically use JSON output and write JSON into the file.
- If you explicitly request `--format text` and also specify an outfile name that ends with `.json`, the script will print an error and exit with a non-zero status to avoid accidental mismatches between the requested text format and a `.json` output file.

Selecting error block representation (`--error-blocks`):

- `grouped` (default): error blocks are grouped under their failure type in JSON (`error_blocks_by_type`), and the text report shows blocks within each failure type section.
- `flat`: error blocks are provided per file in JSON (`error_blocks`) and used directly by the text report.

Examples:

```
# Grouped (default) text
python3 src/evaluate_mvn_builds.py path/to/log/dir --error-blocks grouped

# Flat text
python3 src/evaluate_mvn_builds.py path/to/log/dir --error-blocks flat

# Grouped JSON
python3 src/evaluate_mvn_builds.py path/to/log/dir --format json --error-blocks grouped

# Flat JSON
python3 src/evaluate_mvn_builds.py path/to/log/dir --format json --error-blocks flat
```

JSON output includes counts first for easy consumption:

```
{
  "first_finished_at": "2025-11-27T20:51:00+00:00",
  "last_finished_at": "2025-11-27T21:05:42+00:00",
  "total_evaluated": 12,
  "success_count": 9,
  "failure_count": 3,
  "unreadable_count": 0,
  "failure_type_counts": {
    "Compilation Failure": 2,
    "Dependency Resolution": 1
  },
  "success_files": ["ok1.log", "ok2.log"],
  "failure_files_by_type": {
    "Compilation Failure": ["c1.log", "c2.log"],
    "Dependency Resolution": ["d1.log"]
  },
  "unreadable_files": [],
  "error_blocks": {
    "c1.log": ["[ERROR] ..."],
    "d1.log": ["[ERROR] ..."]
  },
  "error_blocks_by_type": {
    "Compilation Failure": {
      "c1.log": ["[ERROR] ..."],
      "c2.log": ["[ERROR] ..."]
    },
    "Dependency Resolution": {
      "d1.log": ["[ERROR] ..."]
    }
  }
}
```
```

Notes about behaviour
- The script uses namespace-aware matching. It detects the default
  namespace from the root tag so it will match `artifactId` elements
  that live in the same namespace.
- Matching of `artifactId` is exact. If you want case-insensitive or
  substring matching, the script can be extended with flags to alter
  matching behaviour.
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
