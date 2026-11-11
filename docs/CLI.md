# Command-line interface

```shell
codescan --version
codescan scan PATH [--output DIR] [--exclude PATTERN] [--include-hidden] [--force]
codescan scan PATH --encrypt-developer-identities
codescan scan PATH --vulnerability-scan offline --osv-scanner /path/to/osv-scanner
codescan scan PATH --vulnerability-scan online
codescan scan PATH --vulnerability-scan online --license-scan
codescan decrypt-identities ENCRYPTED_FILE
```

A scan writes `report.md`, `files.csv`, and `results.json`. By default the output directory is `PATH/codescan-output`; use `--output` to choose another location. Existing report artifacts are protected unless `--force` is supplied. Repeat `--exclude` to omit matching relative glob patterns. A pattern without `/` matches a path component at any depth; `/` anchors it to the project root; `**` spans zero or more directories. Backslashes are normalized to `/`, so patterns behave consistently on Windows and Linux. Excluding a directory also skips its subtree. Hidden files and folders are excluded by default; `--include-hidden` includes them.

CodeScan skips common generated/vendor folders and does not follow symlinks. It does not execute target project code or make network requests by default. The MVP reports file inventory, basic repository hygiene indicators, conventional test/documentation artifact discovery, parsed supported coverage artifacts, Python AST complexity signals, and locally parsed dependency inventories. Other languages and hosted integrations are not yet measured through complexity analysis.

Both `report.md` and `results.json` record the scan scope: whether hidden files were included, explicit `--exclude` patterns, default ignored directories, and symlink handling.

Developer identity tracking is opt-in. `--encrypt-developer-identities` prompts for a seed twice using a non-echoing terminal prompt, includes seed-scoped developer IDs in the report, and writes names/emails only to an encrypted identity map. `decrypt-identities` prompts for that seed and emits a CSV mapping to standard output. See [Developer identity workflow](DEVELOPER_IDENTITIES.md) for handling guidance.

Vulnerability scanning is disabled by default and requires an installed OSV-Scanner executable. `--vulnerability-scan offline` uses its pre-downloaded local advisory database and performs no network requests. `--vulnerability-scan online` explicitly enables API lookups; CodeScan prints a data-transfer notice before scanning. `--license-scan` adds OSV-Scanner's deps.dev-backed license lookup and requires online mode. Local license file detection is performed without network access and does not interpret terms. Use `--osv-scanner` to select a binary, including a compatible fork build. CodeScan does not download tools or invoke the scanner's remediation commands. See [OSV-Scanner integration](OSV_SCANNER.md).
