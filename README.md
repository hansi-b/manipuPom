# manipuPom

:warning: This utility has mostly been written with the Github Copilot, and I have only superficially checked its adequacy. Seems to be ok, but use at your own risk.

Small utility to read and modify a Maven `pom.xml` using Python's
`xml.etree.ElementTree`.

This repository contains:

- `src/mod_deps.py` — Script to modify dependencies. It can remove
  dependencies by `artifactId`, change the scope of dependencies, and optionally write changes back to the
  POM file. When writing, the script will automatically create a
  `.bak` backup of the original file.
- `tests/data/pom.xml` — an example Maven POM used by the test suite.
- `tests/test_mod_deps.py` — pytest-based unit tests for namespace
  detection and dependency removal.
- `requirements-dev.txt` — development/test dependencies (currently
  contains `pytest`).

## Features

- Detects the root namespace in the POM and registers it as the default
  namespace for serialization, so the output includes a single
  `xmlns="..."` on the root element (no repeated namespace
  declarations on child elements).
- Remove `<dependency>` entries by passing one or more `artifactId`
  values on the command line.
- Change dependency `<scope>` using `--scope artifactId:newScope` format.
- Optionally overwrite the original POM; a `.bak` copy is always
  created before overwriting.

## Requirements

- Python 3.10+
- For running tests: `pytest` (listed in `requirements-dev.txt`).

## Installation / Setup

Recommended: create and activate a virtual environment, then install
dev requirements:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Usage

From the repository root you can run the script directly. The CLI
signature is:

```
python3 src/mod_deps.py <pom-path> [--delete ARTIFACT ...] [--write] [--scope ARTIFACT:SCOPE ...]
```

Examples:

- Print a POM in `someProject` (no changes):

```bash
python3 src/mod_deps.py someProject/pom.xml
```

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

Tests are provided using `pytest` in `tests/test_parse_pom.py`. The
tests exercise namespace detection and that `remove_dependencies`
removes the example artifactIds from `tests/data/pom.xml`.

Run tests with a venv Python (example):

```bash
python -m pytest -q
```

Or with an activated venv that has `pytest` installed:

```bash
pytest -q
```

## Contributing

If you want to add features (for example pattern-based matching for
artifactIds, dry-run mode, or keeping original prefixing for namespaces),
open an issue or submit a PR. Keep changes small and include unit tests.
