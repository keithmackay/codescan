# CodeScan Implementation Phases Summary

## Roadmap

| Phase | Title | Goal | Tasks | Key deliverables |
|---|---|---|---|---|
| 1 | Repository foundation and CLI contract | Establish installable cross-platform package and output schema. | Package/CLI; normalized models; fixtures; docs; CI. | Python CLI skeleton and versioned JSON result. |
| 2 | Local inventory and report output | Complete an end-to-end local scan. | Safe discovery; ten-language mapping; LOC; CSV/JSON/Markdown; integration tests; privacy docs. | `report.md`, `files.csv`, and `results.json`. |
| 3 | Baseline codebase quality signals | Add explainable code, test, docs, and dependency indicators. | Hygiene; test/docs discovery; supported complexity; manifests; rule tests; analyzer docs. | Evidence-backed baseline quality findings. |
| 4 | Git history, contributor concentration, and process evidence | Describe collaboration and key-person risk from local history. | Git metadata; identity mapping; concentration; CI/review artifacts; report caveats; history tests. | Local ownership/process signals with limitations. |
| 5 | OSS vulnerability and license analysis | Add reproducible, opt-in dependency risk checks. | Ecosystem matrix; offline/online modes; advisories; licenses; caching/tests; privacy docs. | Vulnerability and license findings with provenance. |
| 6 | Platform integrations | Add optional read-only hosting and issue-tracker evidence. | Adapter contracts; prioritized GitHub/Azure DevOps; PR/reviews/issues/CI; fixtures; remaining adapters. | Extensible integration framework and first adapters. |
| 7 | AI-agent enhancement surfaces | Enable optional assistant-based interpretation without vendor lock-in. | Redacted input bundle; evidence-grounded prompts; adapters/examples; provenance; privacy. | Optional vendor-neutral agent enhancement layer. |
| 8 | Hardening, release, and maintenance | Prepare a dependable cross-platform release. | Platform/security review; release artifacts; compatibility docs; sample scan; maintenance process. | Versioned release and operations guidance. |

## Technology stack

- Python 3.11+, standard-library core, `pyproject.toml` packaging, `pytest` tests, cross-platform CI.
- JSON as normalized data contract; Markdown reports; UTF-8 CSV file inventory.
- Optional, explicitly detected analyzers and read-only platform adapters; online vulnerability checks opt-in.

## Key principles

- **YAGNI:** deliver the local end-to-end MVP before broad integrations or sophisticated scoring.
- **DRY:** normalize findings and render all outputs from one model; reuse shared analysis logic where licensing and portability allow.
- **TDD:** tests define metric boundaries and output contracts before analyzer behavior expands.
- Preserve evidence, uncertainty, provenance, and limitations; never interpret missing data as failure.
- Frequent, focused commits at each completed task or coherent change.

## Success criteria

- One command scans a local project on Windows and Linux without credentials.
- Markdown, CSV, and JSON outputs are consistent, deterministic, and useful for downstream review.
- Findings cite evidence and disclose confidence, missing access, and limits.
- Default scans do not execute target code or disclose source contents.
- Tests and docs support safe extension by an engineer unfamiliar with the project.

## Post-launch maintenance

Review analyzer accuracy and false positives regularly; update dependency advisory data and supported ecosystems; monitor platform API changes and least-privilege scopes; maintain Windows/Linux CI; version the JSON schema; publish compatibility and deprecation notes; triage security reports; and use analyst feedback to prioritize enhancements.
