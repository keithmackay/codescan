# OSV-Scanner integration

CodeScan integrates OSV-Scanner as an optional executable. This keeps vulnerability matching and ecosystem parsing in the OSV tool while CodeScan combines its findings with the project assessment. CodeScan keeps its lightweight local dependency inventory as separate evidence.

## Install and select the tool

Install a supported OSV-Scanner v2 release separately, following its official installation and release-verification guidance. CodeScan does not download or update the executable. By default it looks for `osv-scanner` on `PATH`; pass `--osv-scanner PATH` to select another binary. This can point to a compatible build of `keithmackay/osv-scanner`; report normalization is based on the documented JSON output, so verify compatibility when changing versions.

The recommended default source is an official upstream release. The named fork is a valid override for testing or when it contains a needed change, but should be kept current with upstream. At review time, GitHub's compare pages showed the fork 69 upstream scanner commits behind and the SCALIBR fork 176 commits behind, with no fork-only commits reported:

- [OSV-Scanner fork comparison](https://github.com/google/osv-scanner/compare/main...keithmackay:main)
- [OSV-SCALIBR fork comparison](https://github.com/google/osv-scalibr/compare/main...keithmackay:main)

## Scan modes

Vulnerability scanning is disabled unless the user selects a mode:

```shell
# Uses an already downloaded local advisory database; no network traffic.
codescan scan ./project --vulnerability-scan offline

# Explicitly queries OSV.dev; CodeScan prints a notice before running.
codescan scan ./project --vulnerability-scan online
```

Offline mode does not download or update database files. It reports an incomplete analyzer status if the local database is unavailable. Online mode sends package names, versions, and ecosystems to OSV.dev. Package license lookup is a separate explicit feature:

```shell
codescan scan ./project --vulnerability-scan online --license-scan
```

It uses OSV-Scanner's license feature, whose data comes from deps.dev. CodeScan does not set an allowlist or make a legal-risk conclusion; it records returned SPDX identifiers and scanner-reported violations for review. Local detection of root-level LICENSE/COPYING/NOTICE files remains offline and only reports their presence. CodeScan never enables guided remediation. Review [OSV-Scanner's data and privacy documentation](https://google.github.io/osv-scanner/usage/) when upgrading the scanner.

## Normalized evidence

CodeScan stores scanner output in the existing `results.json` as normalized vulnerability records: advisory ID and aliases, package name, ecosystem, resolved version, fixed versions when the advisory provides them, severity when supplied, relative source path, and source tool. When license lookup is enabled, normalized package/license records are also stored. Markdown links each advisory to OSV.dev. Absolute paths from scanner output are converted to paths relative to the scan root; paths outside the root are reduced to their basename.

Scanner version, mode, result count, and partial/failed state appear in analyzer status. Exit code 1 is treated as a successful scan with findings; other nonzero result codes are partial and any parsed findings remain available. Missing executable and missing offline database are never reported as “no vulnerabilities.”

CodeScan never runs `osv-scanner fix`, package managers, or project build scripts. It does not auto-install the scanner. Ordinary tests use recorded synthetic JSON and mocked subprocess results; they do not contact OSV.dev.

## Why SCALIBR is not embedded directly

OSV-SCALIBR is a Go library for software composition analysis, SBOM generation, and broader inventory including container analysis. Embedding it directly would require a Go bridge and create a second integration surface. OSV-Scanner already uses SCALIBR and exposes both vulnerability results and SBOM formats, so the executable adapter is the simpler fit for CodeScan's current Python CLI. A direct SCALIBR bridge can be reconsidered if CodeScan later needs inventory or container capabilities unavailable through OSV-Scanner's interface.

## Sources

- [OSV-Scanner JSON output](https://google.github.io/osv-scanner/output/)
- [OSV-Scanner offline mode](https://google.github.io/osv-scanner/usage/offline-mode/)
- [OSV-Scanner installation and release verification](https://google.github.io/osv-scanner/installation/)
- [OSV-SCALIBR README](https://github.com/google/osv-scalibr)
- [OSV API documentation](https://google.github.io/osv.dev/api/)
