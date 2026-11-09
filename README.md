# CodeScan

## Description

CodeScan is a portable, script-first command-line tool for assessing a software project from a working folder. It produces evidence-backed Markdown assessment reports and CSV inventories for codebase size and language, code quality, tests, documentation, development process maturity, contributor concentration, dependency vulnerabilities, and license risk. The MVP prioritizes useful local scans on Linux and Windows, with optional adapters for repository hosting and issue tracking platforms. AI-agent skills and adapters can enrich analysis while the core scan remains usable without a particular assistant. Outputs are designed to be shared by email or placed in a project data room for further review.

## Installation

Requires Python 3.11 or newer.

```shell
python -m pip install .
```

For development, install `python -m pip install -e ".[dev]"`.

## Usage

```shell
codescan --version
codescan scan PATH --output OUTPUT_DIR
```

The initial release is under development. The CLI currently validates the project path; full inventory and report generation are planned for Phase 2. CodeScan does not execute project code by default.

## License

Proprietary. See the repository owner for licensing terms.
