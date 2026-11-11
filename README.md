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
# Optional: query OSV.dev (requires OSV-Scanner)
codescan scan PATH --vulnerability-scan online
# Optional package license metadata via deps.dev (online only)
codescan scan PATH --vulnerability-scan online --license-scan
```

The MVP scans local files and writes a Markdown report, CSV inventory, and normalized JSON results. Optional developer tracking uses seed-scoped IDs and an encrypted identity map; see [Developer identity workflow](docs/DEVELOPER_IDENTITIES.md). Scanning is local-only by default. Online vulnerability and package license lookups require explicit options; see [OSV-Scanner integration](docs/OSV_SCANNER.md). LOC means nonblank physical lines; language is inferred from file extension. More quality and hosted-service analyzers are planned for later phases.

## License

Proprietary. See the repository owner for licensing terms.
