# CodeScan Implementation Plan

## Goal and scope

Deliver a portable command-line scanner that accepts a local repository path and produces a reproducible Markdown report, machine-readable structured data, and a CSV file inventory. Build a modest end-to-end MVP first, then add analyzer and platform coverage incrementally. The scanner must distinguish observed evidence, inferred findings, unavailable data, and unsupported checks. It must not label missing evidence as poor practice.

## Initial product decisions

- Runtime: Python 3.11+ with standard-library core; optional analyzers are detected and reported. This supports Windows and Linux and keeps installation simple.
- CLI: `codescan scan PATH --output DIR`; default local-only operation, no credentials required.
- Output: `report.md`, `files.csv`, and `results.json`; deterministic schemas and timestamps/run metadata.
- File inventory includes relative path, detected language, byte size, total lines, blank lines, and comment lines where safely measurable. Avoid following symlinks outside the target.
- Initial ten language targets: C#, Java, JavaScript, TypeScript, Python, C/C++, Go, PHP, Ruby, and SQL. Detection is extension-based and disclosed; language-specific metrics are enabled only where reliable.
- Repository platforms: GitHub, GitLab, Azure DevOps, Bitbucket, and TFVC/TFS. Issue trackers: Jira, Azure Boards, GitHub Issues, GitLab Issues, and YouTrack. Local mode is the MVP; integrations follow as separate phases.
- No aggregate quality score in MVP. Findings include severity, evidence, confidence, limitations, and suggested follow-up.
- Ignore generated/vendor/build directories and honor common ignore files where practical; allow explicit include/exclude overrides.
- Never execute target project code by default. External tool execution is opt-in, time-bounded, and recorded.

## Reuse inventory

Before porting any code, inspect licensing, dependencies, privacy assumptions, and whether scripts can run on Windows/Linux. Do not copy project-specific datasets or credentials.

- `../ssg-project-compass`: sanitized examples and repository hygiene, CI/CD, test coverage, developer ownership, SQL migration, and extraction-candidate analyses. Candidate evidence/report patterns; sanitized inputs only.
- `../EY_WorkingSpace/scripts/107-scan_dependencies.py`: dependency discovery concepts; `analyze_co2_test_coverage.py`, `040-analyze_co3_e2e_tests.py`, `051-analyze_co3_developer_profiles.py`, `analyze_co2_git_commits.py`, `176-extract_git_history.py`, and `code_symbols_common.py`: candidate test, ownership, history, and symbol-analysis logic. Review imports and portability before adapting.
- `../Varsity/scripts/analyze_functions.py`, `generate_tal_code_coverage_report.py`, `developer_profile_analysis.py`, `analyze_git_commits_module_level.py`, `jira_client.py`, and `generate_composite_reports.py`: candidate complexity, coverage, ownership, Jira adapter, and report-generation patterns. These are project-specific and require isolation from Varsity assumptions.
- Reuse decision log: record source path, license, changes, and attribution in `docs/reuse/REUSE.md` before any code is copied or adapted.

## Architecture and data contracts

Use a small package with clear boundaries: CLI/orchestration, file discovery, analyzers, integrations, normalized models, and renderers. An analyzer returns structured findings and a status (`completed`, `partial`, `skipped`, `failed`) with evidence references. Keep collection separate from interpretation and rendering. Persist normalized JSON first; render Markdown and CSV from that model. Redact secrets and avoid including source excerpts by default. All report paths are relative to the scanned root.

### Proposed initial layout

- `pyproject.toml`: package metadata, supported Python, entry point, dev/test dependencies.
- `src/codescan/cli.py`: argument parsing and exit codes.
- `src/codescan/scan.py`: orchestration and run metadata.
- `src/codescan/discovery.py`: safe file walking, ignore/exclude handling, language mapping.
- `src/codescan/models.py`: versioned normalized result and finding structures.
- `src/codescan/analyzers/`: inventory, repository hygiene, tests/docs, complexity, dependencies.
- `src/codescan/integrations/`: platform adapters introduced in later phases.
- `src/codescan/renderers/`: Markdown, CSV, JSON output.
- `tests/`: unit, integration, and fixture repositories.
- `docs/`: CLI, output schema, analyzers, integrations, privacy, and operations guidance.

## Phase 1 — Repository foundation and CLI contract

Goal: create an installable, testable Python CLI skeleton and freeze the output contract.

1. Add `pyproject.toml`, package structure, supported Python versions, and `codescan` console entry point. Keep runtime dependencies empty initially.
2. Implement `codescan scan PATH --output DIR`, `--version`, and helpful usage errors. Validate path and output behavior; use stable nonzero exit codes for invalid input and fatal scan failures.
3. Define versioned models in `models.py`: run metadata, analyzer status, finding, evidence, and limitations. Add JSON serialization with schema version.
4. Define fixtures for empty, ordinary, ignored, and malformed repositories under `tests/fixtures/`.
5. Document setup and CLI contract in README and `docs/CLI.md`; record test conventions in `docs/TESTING.md`.
6. Add CI for Linux and Windows with the minimum and latest supported Python; run unit tests and formatting/lint checks.

Deliverable: installable skeleton whose CLI validates inputs and writes a minimal, schema-versioned result.

## Phase 2 — Local inventory and report output (MVP end-to-end)

Goal: generate useful outputs from any ordinary local repository.

1. Implement safe recursive discovery: skip `.git`, common generated/vendor directories, symlink escapes, and configurable exclusions; add `--exclude` and `--include-hidden` options.
2. Implement extension-based mapping for the ten initial languages listed above; unknown files remain `unknown` rather than being guessed.
3. Calculate per-file LOC, blank lines, and byte size consistently. Define treatment of CRLF, empty files, and final newline in tests. Comment LOC is optional and only reported when language parsing is reliable.
4. Generate `files.csv` with documented UTF-8 encoding, stable columns, path separators, and deterministic sorting.
5. Generate `results.json` and `report.md`, including scan scope, summary counts, findings, analyzer coverage/status, limitations, and environment metadata. Report no score until calibration evidence supports one.
6. Add integration tests that run the installed CLI against fixtures and validate all three outputs and cross-file consistency.
7. Document report sharing and privacy behavior, including that source contents are not copied into reports by default.

Deliverable: complete local scan workflow with CSV inventory and readable Markdown report on Windows/Linux.

## Phase 3 — Baseline codebase quality signals

Goal: add low-cost, explainable findings without overstating static heuristics.

1. Add repository hygiene checks for oversized files, likely generated code, common secrets-file names, TODO/FIXME markers, and suspiciously large modules. Do not print secret values.
2. Add test and documentation discovery using conventional directory/file names, manifests, coverage artifacts, and README presence. Distinguish detected tests from measured coverage.
3. Add complexity metrics only through available, language-appropriate parsers/tools. Report tool/version, thresholds, exclusions, and whether analysis was partial. Do not claim a universal complexity metric across unsupported languages.
4. Add dependency manifest discovery for the supported ecosystems and normalize package name, declared constraint, and lockfile-resolved version when present.
5. Add unit and fixture tests per rule, including false-positive boundaries. Ensure deterministic results and bounded memory on large files.
6. Document every metric's meaning, evidence source, known bias, and limitation in `docs/ANALYZERS.md`.

Deliverable: baseline code, test, documentation, and dependency signals with traceable evidence.

## Phase 4 — Git history, contributor concentration, and process evidence

Goal: describe collaboration and key-person risk from available repository history.

1. Detect Git repositories and collect commit metadata locally using a library or Git executable only when available; never fetch or mutate remote state.
2. Normalize author identities conservatively and allow an optional local mapping file; disclose aliases and uncertainty.
3. Compute commit and file-change concentration by contributor and time window. Avoid equating commit count with productivity or skill.
4. Detect PR/review and CI/CD configuration artifacts in repository files. Local artifacts are evidence of configuration, not proof of use or effectiveness.
5. Add report sections for contributor concentration, test/process artifacts, collection window, missing history, and interpretation caveats.
6. Add fixture Git repositories and tests for shallow history, renamed authors, empty history, and date boundaries.
7. Document key-person risk as a prompt for human review, not a personnel judgment.

Deliverable: local collaboration and process signals with explicit limitations.

## Phase 5 — OSS vulnerability and license analysis

Goal: identify dependency risk using reproducible, opt-in data sources.

1. Build an ecosystem-to-manifest/lockfile matrix and prioritize the ecosystems most common among the initial languages.
2. Define an offline mode and an opt-in online mode. Online checks must identify source, database freshness, and query time; credentials must come from environment or OS credential store, never CLI arguments.
3. Compare resolved versions against a selected vulnerability database or scanner adapter. Report affected package/version, advisory identifier, severity/source, and remediation version only when sourced.
4. Detect declared licenses and package license metadata where available; flag unknown or conflicting terms for review rather than issuing legal conclusions.
5. Cache advisory data with explicit freshness and provide reproducible fixtures; handle network failures as partial analysis.
6. Add privacy documentation explaining what package metadata leaves the machine and how to disable online checks.

Deliverable: opt-in dependency vulnerability and license findings with provenance and freshness.

## Phase 6 — Platform integrations: repository management and issue tracking

Goal: add optional hosted evidence through adapter interfaces.

1. Finalize adapter contracts and capability matrix for GitHub, GitLab, Azure DevOps, Bitbucket, TFVC/TFS and Jira, Azure Boards, GitHub Issues, GitLab Issues, YouTrack.
2. Implement one priority integration at a time, beginning with GitHub and Azure DevOps based on initial user needs; support read-only least-privilege access and pagination/rate-limit handling.
3. Support explicit project/repository identifiers and time windows. Never infer an organization or upload scan outputs.
4. Collect PR/review metrics, issue activity, reviewer distribution, and CI run/config signals only where API permissions allow. Record permissions and unavailable capabilities.
5. Add recorded API fixtures and contract tests; keep secrets out of logs/reports. Document per-platform scopes and setup.
6. Add remaining platform adapters incrementally only after the first integration has stable contracts.

Deliverable: extensible, opt-in read-only platform evidence adapters.

## Phase 7 — AI-agent enhancement surfaces

Goal: let different coding assistants interpret structured outputs without coupling core scans to a vendor.

1. Define a stable agent input bundle based on redacted `results.json` and selected report sections.
2. Create vendor-neutral prompts/instructions for validating evidence, drafting questions, and summarizing findings; require citations to finding IDs and prohibit unsupported conclusions.
3. Package optional skill/adaptor examples for Claude, Codex, Gemini, Factory Droid, Devin, and Cursor where their extension mechanisms permit. Keep installation optional and separate from core CLI.
4. Add generated output provenance, model/tool name, prompt version, and human-review labels; never overwrite deterministic scan data.
5. Document privacy controls and ensure AI mode is opt-in with user-controlled data submission.

Deliverable: optional agent-assisted interpretation over stable local artifacts.

## Phase 8 — Hardening, release, and maintenance

Goal: prepare a dependable cross-platform release.

1. Test a matrix of Windows and Linux versions, path encodings, permissions, CRLF, large repositories, and offline operation.
2. Review dependency footprint, license inventory, secret handling, symlink/path traversal safety, and subprocess timeouts.
3. Add release versioning, changelog, reproducible package build, signed/checksummed artifacts if practical, and install/upgrade instructions.
4. Publish supported-platform and analyzer capability matrices; document schema compatibility and deprecation policy.
5. Perform a sample scan of a non-sensitive fixture repository and manually review whether each report claim is supported by evidence.
6. Establish issue triage, vulnerability update cadence, analyzer accuracy review, and compatibility maintenance.

Deliverable: versioned release with operational and maintenance documentation.

## Testing strategy

Use pytest and temporary/fixture repositories. Unit tests cover pure functions and boundaries; integration tests invoke the CLI and validate generated artifacts; platform adapter tests use recorded responses; cross-platform CI checks path and encoding behavior. Add regression fixtures for each discovered false positive. Tests should assert observable behavior and schemas, not private implementation details. Run formatting, lint, type checks, and test suite in CI. Do not make network calls in ordinary tests.

## Documentation checklist

Maintain README quick start; CLI reference; output schema; per-analyzer definitions and limitations; integration permissions; data handling/privacy; development and test setup; release and troubleshooting guides; reuse attribution. Keep examples synthetic and safe to share.

## Definition of done

- A user can install CodeScan on supported Windows and Linux versions and scan a local repository without credentials.
- One command emits Markdown, CSV, and JSON artifacts with consistent inventory data.
- Analyzer coverage, evidence, uncertainty, and failures are visible in reports.
- No target code is executed by default and reports do not include source contents or secret values.
- Automated tests validate core contracts on both operating systems.
- Documentation enables an engineer unfamiliar with the codebase to run, interpret, and extend the tool.

## Next Steps

- [Keith's idea] Expand analyzer coverage and integration depth based on real due diligence engagements and analyst feedback.
- [Keith's idea] Add secure data-room packaging and standardized export bundles for repeatable handoff.
- [Claude's idea] Add baseline comparison between two scans to identify architectural and risk trends over time.
- [Claude's idea] Add configurable organization profiles for thresholds and report emphasis while preserving raw metrics.
