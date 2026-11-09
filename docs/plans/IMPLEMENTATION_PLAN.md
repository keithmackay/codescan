# CodeScan Implementation Plan

## 1. Mission and delivery sequence

Build CodeScan as a portable, script-first command-line tool that scans a local software project and produces a Markdown assessment, a CSV file inventory, and normalized JSON data. Deliver a useful local-only MVP before adding hosted-service integrations or AI interpretation. Every conclusion must point to evidence and state its scope and limits. A missing artifact, unavailable API, unsupported language, or incomplete history is reported as unknown or unavailable, never as proof of poor practice.

The plan assumes an engineer has no prior knowledge of CodeScan, the business context, or the sibling projects. Each phase ends in an independently reviewable deliverable. Keep commits small and coherent, ideally one commit for each numbered task or closely related pair.

## 2. Product decisions for the initial release

- **Runtime and packaging:** Python 3.11+, packaged with `pyproject.toml`, runnable on supported Linux and Windows versions. Keep the required runtime dependency set small; every new dependency needs a reason and license review.
- **Primary command:** `codescan scan PATH --output DIR`. It runs locally without credentials and does not execute scanned-project code.
- **Output bundle:** `report.md`, `files.csv`, and `results.json`, written to a new or explicitly selected output directory. JSON is the normalized data contract; other outputs are renderings of the same result model.
- **Initial language coverage:** C#, Java, JavaScript, TypeScript, C/C++, Go, Python, PHP, Ruby, and SQL. State that these are a practical starting set, not a ranking claim. Extension mapping is deterministic; unknown extensions remain unknown.
- **Initial repository-management targets:** GitHub, GitLab, Azure DevOps, Bitbucket, and TFVC/TFS. **Issue-tracker targets:** Jira, Azure Boards, GitHub Issues, GitLab Issues, and YouTrack. TFVC/TFS and Azure DevOps overlap in product history; keep product and protocol terminology explicit in docs.
- **MVP analysis:** file inventory/LOC/language, repository structure and hygiene, discoverable test and documentation signals, basic Git-history concentration when history exists, and CI/CD configuration evidence. Dependency vulnerability and license checks are an opt-in later capability.
- **No single quality score in MVP.** Report indicators independently with evidence, measurement method, severity where meaningful, confidence/limitations, and analyst follow-up questions.
- **Privacy:** do not copy source contents into output; do not follow symlinks outside the scan root; do not upload scan results. Online lookups and hosted adapters require explicit opt-in.

## 3. Existing repository and reuse inventory

The current repository is a template-derived documentation scaffold with no application package yet. Before adapting code, inspect source headers, repository licenses, dependencies, data handling, hard-coded project assumptions, and Windows compatibility. Do not copy datasets, credentials, customer names, or sensitive outputs. Record each reuse decision in `docs/reuse/REUSE.md`; if no code is reused, record why.

Candidate sources to inspect:

- `../ssg-project-compass`: sanitized repository hygiene, CI/CD, E2E coverage, developer ownership, SQL migration, and extraction-candidate analyses. Use these as examples of report questions and evidence presentation; verify that the exact scripts are available before selecting code.
- `../EY_WorkingSpace/scripts/107-scan_dependencies.py`: dependency-discovery candidate; `analyze_co2_test_coverage.py`, `040-analyze_co3_e2e_tests.py`, `051-analyze_co3_developer_profiles.py`, `analyze_co2_git_commits.py`, `176-extract_git_history.py`, and `code_symbols_common.py`: candidates for test, ownership, history, and symbol logic. Review imports and portability; the surrounding repository may contain private/project-specific assumptions.
- `../Varsity/scripts/analyze_functions.py`, `generate_tal_code_coverage_report.py`, `developer_profile_analysis.py`, `analyze_git_commits_module_level.py`, `jira_client.py`, and `generate_composite_reports.py`: candidate complexity, coverage, contributor, Jira, and report patterns. Do not import them directly until isolated from Varsity-specific configuration and data.

Task gate: inspect candidates with `rg`, read relevant code and license metadata, and write a reuse matrix with columns `source`, `candidate capability`, `license`, `dependencies`, `portability`, `sensitive assumptions`, `decision`. Prefer a small rewrite of a clearly understood algorithm over pulling in a large script with hidden coupling.

## 4. Architecture and shared contracts

Use a small package with boundaries that let local analyzers, hosted adapters, and renderers evolve independently. The orchestration layer calls collectors/analyzers, gathers typed results, and passes one normalized model to all renderers. Do not let renderers rescan files or independently calculate metrics.

### Proposed source tree

```text
pyproject.toml
src/codescan/
  __init__.py
  __main__.py
  cli.py
  scan.py
  config.py
  discovery.py
  models.py
  analyzers/
    __init__.py
    inventory.py
    repository.py
    tests_docs.py
    git_history.py
    dependencies.py
  integrations/
    __init__.py
    base.py
    github.py
    gitlab.py
    azure_devops.py
    bitbucket.py
    jira.py
  renderers/
    __init__.py
    markdown.py
    csv.py
    json.py
tests/
  fixtures/
  unit/
  integration/
docs/
  CLI.md
  OUTPUT_SCHEMA.md
  ANALYZERS.md
  PRIVACY.md
  INTEGRATIONS.md
  DEVELOPMENT.md
  reuse/REUSE.md
```

Start only with modules needed for a phase. Do not create empty adapters or speculative plugin infrastructure. A future integration is introduced when its phase begins.

### Normalized result contract

Define and document a schema-versioned result containing: scan ID; CodeScan version; start/end times in UTC; root label (avoid absolute user paths in portable output); options that affect scope; discovered file counts; language totals; analyzer records with `completed`, `partial`, `skipped`, or `failed`; findings with stable IDs, category, title, severity/priority if applicable, summary, evidence references, confidence/limitations, and remediation/follow-up; and errors sanitized of secrets. Evidence identifies a relative file path and line/metric/API source without embedding source text by default. CSV columns are stable, UTF-8, sorted by normalized relative path, and include at minimum `path`, `language`, `loc`, `blank_lines`, and `bytes`.

## 5. Phase 1 — Package, developer workflow, and CLI contract

**Goal:** create an installable, cross-platform skeleton and freeze the minimum public CLI and result contracts.

### Tasks

1. **Inspect scaffold and set project conventions.** Review `AGENTS.md`, `CLAUDE.md`, `.claude/commands/`, and `docs/TESTING_GUIDELINES.md`. Decide which template files remain relevant; remove or revise only clearly unrelated guidance. Create `docs/reuse/REUSE.md` with the reuse review table. Commit: `docs: record project conventions and reuse review`.
2. **Create packaging metadata.** Add `pyproject.toml` with package name `codescan`, Python floor, build backend, console entry point, and dev extras for pytest, formatter/linter, and type checker. Keep runtime dependencies empty. Add `.python-version` only if the chosen tooling needs it. Test install into a clean virtual environment on the developer OS. Commit: `build: add Python package metadata and CLI entry point`.
3. **Create the smallest package.** Add `src/codescan/__init__.py`, `__main__.py`, `cli.py`, and `scan.py`. `codescan --version` and `codescan scan --help` must work. Use `argparse` unless a demonstrated need justifies a CLI dependency. Commit: `feat(cli): add codescan command skeleton`.
4. **Define result models and JSON serialization.** Add dataclasses or similarly simple typed structures in `models.py` for run metadata, analyzer status, evidence, findings, and scan result. Define `schema_version`; serialize predictably and reject unsupported schema versions in any future reader. Unit tests assert required fields, enum values, stable JSON types, and serialization round trip. Commit: `feat(core): define versioned scan result model`.
5. **Define exit behavior.** Invalid path/arguments use usage errors; scan-level analyzer failures should be represented in results and not hide other analyzer results; fatal output or orchestration failures return a documented nonzero code. Add CLI tests for each exit class. Commit: `test(cli): cover arguments and exit behavior`.
6. **Add CI and contributor guide.** Configure GitHub Actions for Ubuntu and Windows with minimum and latest supported Python. Install package and dev extras, run lint/format check, type check, and pytest. Add `docs/DEVELOPMENT.md` with setup, commands, style and test expectations. Commit: `ci: add Windows and Linux quality checks`.

### Phase 1 acceptance

- Fresh environment can install the project and invoke `codescan`.
- Help/version commands and model tests pass.
- CI runs on Windows and Linux; failures are actionable.
- Output schema decisions are documented before any analyzer-specific fields proliferate.

## 6. Phase 2 — Local inventory and end-to-end MVP

**Goal:** scan a local folder and emit mutually consistent CSV, JSON, and Markdown artifacts.

### Tasks

1. **Specify file discovery behavior first.** Add fixture trees for ordinary source, hidden files, ignored folders, symlinks, unreadable files, Unicode names, CRLF, empty files, and nested repositories. Document defaults and CLI overrides in `docs/CLI.md`.
2. **Implement safe discovery.** Add `discovery.py` to walk without following symlinks by default, exclude `.git` and standard build/vendor/cache folders, support repeatable `--exclude` patterns and explicit hidden-file behavior, and normalize relative paths to `/` in outputs. Confirm exclusions never escape or expand beyond the requested root. Test each boundary with temporary directories.
3. **Implement language mapping.** Add a centralized extension table for the ten initial languages, including ambiguous extensions and a documented precedence rule. Use `unknown` when uncertain. Add table-driven tests for each extension and unknown cases; avoid directory-name guessing.
4. **Implement inventory metrics.** Add `analyzers/inventory.py` to count physical lines, blank lines, byte size, and language. Define LOC as nonblank physical lines initially; preserve total line and blank line values separately. Do not call these comment-aware source lines. Handle UTF-8 decode errors without crashing the whole scan; record file-level unreadable/unsupported status. Tests cover empty file, final newline/no final newline, CRLF, invalid UTF-8, and binary files.
5. **Build a minimal scan orchestrator.** `scan.py` should create run metadata, invoke discovery and inventory, collect statuses, and return the model. No analyzer should write report files directly. Test with fixtures.
6. **Render CSV and JSON.** Implement `renderers/csv.py` and `renderers/json.py`. Use deterministic ordering and explicit newline handling; write UTF-8. Test headers, quoting for commas/newlines, stable ordering, schema version, and totals matching model data.
7. **Render Markdown report.** Implement `renderers/markdown.py` with scope, run metadata, inventory summary, language table, analyzer status, exclusions, and limitations. Avoid unsupported quality judgments at this phase. Test required sections and ensure all values come from result model.
8. **Wire output CLI.** Add `--output`, `--exclude`, and hidden-file option; create output directory safely, refuse accidental overwrite unless `--force` is supplied, and write outputs atomically where practical. Add integration tests invoking `python -m codescan` and installed console entry point.
9. **Document output and privacy.** Add `docs/OUTPUT_SCHEMA.md`, `docs/PRIVACY.md`, and `docs/CLI.md`; update README Installation/Usage with environment setup and example. Explain that source text is not emitted and all output files should be reviewed before sharing.

### Phase 2 acceptance (MVP launch gate)

- A local-only command works without API credentials or optional analyzer tools.
- A scan emits `report.md`, `files.csv`, and `results.json` with matching file/language/LOC totals.
- A malformed or unreadable individual file is reported and does not abort a useful scan.
- Identical inputs/options produce identical inventory ordering and metric values; volatile timestamps are isolated in metadata.
- Windows and Linux CI pass the integration suite.

## 7. Phase 3 — Repository, tests, documentation, and code signals

**Goal:** add first-pass quality and maturity indicators that are explainable and not presented as universal scores.

### Tasks

1. **Define metrics and evidence before rules.** Extend `docs/ANALYZERS.md` with a table: metric, definition, input, coverage, caveat, evidence format. For each metric, write positive, negative, and unknown fixture scenarios before implementation.
2. **Repository structure/hygiene analyzer.** Add `analyzers/repository.py` for large files, generated/vendor hints, likely secret-file names, TODO/FIXME counts, root organization, and presence of common config files. Never read or emit secret contents; test with fake markers and false-positive cases. Findings should be descriptive, not automatic severity judgments.
3. **Test/documentation discovery.** Add `analyzers/tests_docs.py` for conventional test directories/files, test manifests, README/docs presence, coverage artifacts, and CI configs. Clearly separate “tests detected,” “coverage artifact found,” and “coverage percentage measured.” A coverage percentage is only reported when a supported coverage artifact supplies it.
4. **Optional complexity analyzer decision.** Evaluate reusable parsers and tool requirements. Implement only metrics with reliable parsing for named languages; document language coverage and parser versions. Start with one supported language and a small set of metric rules; add more only when tests establish accuracy. Do not approximate complexity with naïve keyword counts.
5. **Analyzer registration and fault isolation.** Add a minimal internal analyzer sequence in `scan.py` (not a generic plugin API). A failed analyzer yields a failed status/error and other analyzers continue. Add tests for exceptions and partial outputs.
6. **Findings and report sections.** Add structured evidence references and render sections grouped by category. Ensure Markdown escapes project-controlled text. Verify no findings are silently dropped from JSON or report.
7. **Reuse review and adaptation.** Compare task 1 inventory results with Compass/EY/Varsity candidates; adapt only isolated, licensed, portable logic. Add provenance and tests to `docs/reuse/REUSE.md`. Avoid wholesale script copies.
8. **Test quality and docs.** Add rule-level unit tests, end-to-end fixture scans, and regression tests for false positives. Update `docs/ANALYZERS.md` for every shipped signal.

### Phase 3 acceptance

- Every shipped finding has a documented detection rule and evidence trail.
- Unknown/unsupported input produces a limitation or status, not a fabricated score.
- Secret scans never echo matched values.
- Tests/docs/coverage signals have distinct meanings in JSON and Markdown.

## 8. Phase 4 — Git history, contribution density, and process signals

**Goal:** describe contributor concentration and visible engineering practices using local Git metadata and repository artifacts.

### Tasks

1. **Define analysis window and privacy model.** Document default history window (initially all locally available history, with explicit `--since`/`--until` options), shallow-clone detection, author identity limitations, and what metadata is collected. Do not collect email addresses into report by default.
2. **Implement safe Git metadata collection.** Add `analyzers/git_history.py`. Prefer a well-maintained library only if it is portable; otherwise invoke Git read-only with argument arrays, timeouts, bounded output, and clear missing-Git status. Never fetch, checkout, or mutate the target repository. Test no Git, shallow repo, empty repo, and command timeout.
3. **Compute contribution measures.** Calculate commits and changed-file counts by normalized author and time period; optionally compute file ownership concentration from changed lines only if the method is reliable. Label these as activity/concentration signals, not productivity, quality, or individual performance. Do not rank named developers in the default report.
4. **Support explicit identity mapping.** Accept an optional user-provided mapping file path; do not auto-merge identities based on similar names. Keep raw author identifiers out of output unless explicitly configured. Test aliases and privacy defaults.
5. **Inspect process artifacts.** Detect PR/review templates, CODEOWNERS, CI workflows, branch policy docs, and common build/test pipelines. Say “configuration artifact detected,” not “process is followed.”
6. **Render history limits.** Add report sections for window, commit count, shallow/missing history, unmapped identities, and interpretation caveats. Missing API evidence is listed as unavailable.
7. **Build Git fixtures and docs.** Generate small temporary Git repositories in tests; cover time zones, date boundaries, merge commits, renames where supported, and authorship mappings. Update `docs/ANALYZERS.md` and `docs/PRIVACY.md`.

### Phase 4 acceptance

- History collection is read-only and bounded by timeout.
- Contributor concentration is aggregated with clear limits and no performance ranking.
- Shallow or missing history is visible and does not become a negative finding.

## 9. Phase 5 — Dependency, vulnerability, and license risk

**Goal:** discover dependencies and optionally assess known vulnerabilities and license metadata with clear provenance.

### Tasks

1. **Build ecosystem support matrix.** Map supported manifests and lockfiles to ecosystems and language coverage. Prioritize actual enterprise repo prevalence and reusable parsers; list unsupported formats explicitly.
2. **Implement offline dependency extraction.** Add `analyzers/dependencies.py` to parse declared constraints and resolved versions from lockfiles without executing package managers. Add fixtures for common manifests, malformed files, duplicate packages, and version ranges.
3. **Choose advisory data source.** Compare a maintained local scanner/database approach with an opt-in API. Document data licensing, freshness, identifiers, rate limits, and package metadata sent externally before enabling online mode. Make `--offline` the default.
4. **Implement vulnerability adapter.** Normalize package, ecosystem, resolved version, advisory ID, source, severity as provided, affected range, fixed version, and database timestamp. Never infer a fixed version. Test using recorded advisory fixtures; ordinary tests make no network calls.
5. **Implement license evidence.** Read declared license files/metadata and package metadata when available. Report unknown/conflicting values for legal review; do not provide legal conclusions. Include source and confidence.
6. **Add cache and failure behavior.** Cache with source and timestamp; define max age. Network or database errors produce partial status with guidance, not an empty “no vulnerabilities” result.
7. **Document network/privacy behavior.** Update `docs/PRIVACY.md`, `docs/ANALYZERS.md`, and `docs/CLI.md`, including opt-in flags and exact metadata transmitted.

### Phase 5 acceptance

- Offline dependency inventory works without package-manager execution.
- Online advisory checks are explicit, attributable, cache-aware, and tested without live-network dependency.
- “No known findings in queried source” is distinct from “not checked.”

## 10. Phase 6 — Repository-management and issue-tracker adapters

**Goal:** add optional, read-only hosted evidence via common contracts, prioritizing one integration at a time.

### Tasks

1. **Write adapter contract and capability matrix.** Add `integrations/base.py` with explicit auth, configuration, capabilities, collection window, status, and normalized evidence. Document the ten requested products and their overlapping product boundaries in `docs/INTEGRATIONS.md`.
2. **Select first adapter using user value and testability.** Start with GitHub unless discovery establishes a stronger priority. Support explicit organization/repository, read-only scopes, pagination, rate limits, and user-selected date range. No automatic organization discovery.
3. **Add recorded API fixtures.** Redact tokens, user data, and private project details. Test pagination, permission denied, rate limited, deleted item, and partial API response. No live credentials in CI.
4. **Add PR/review/issue evidence.** Collect only defined metrics such as PR count, review events, reviewer distribution, issue status/activity, and linked CI metadata. Document sampling windows and missing permissions.
5. **Add Azure DevOps, GitLab, Bitbucket, Jira, Azure Boards, and YouTrack one adapter at a time.** Each adapter gets a capability page, minimum-scope setup, tests, and report status. Treat TFVC/TFS as its own protocol/platform case; do not claim compatibility merely because Azure DevOps is supported.
6. **Credential controls.** Read tokens from environment or supported OS credential store; never accept tokens as CLI argument, write them to reports, or log request headers. Provide redaction tests.
7. **Integration opt-in.** Add explicit flags/config selection; local-only is the default. Never upload scan outputs or source code.

### Phase 6 acceptance

- Every integration is opt-in, read-only, least-privilege, and reports its actual capability/access status.
- A failure or permission gap leaves useful local analysis intact.
- No secrets appear in logs, artifacts, fixtures, or exception output.

## 11. Phase 7 — Agent-assisted interpretation

**Goal:** let users apply different coding assistants to normalized findings without making CodeScan depend on a vendor.

### Tasks

1. Define a redacted input bundle based on `results.json`, finding IDs, and selected report sections. Exclude absolute paths and raw contributor identifiers unless explicitly enabled.
2. Create a vendor-neutral prompt/instruction contract: cite finding IDs, distinguish evidence from inference, ask questions for gaps, do not invent metrics, and label human review as required.
3. Add example integrations for Claude, Codex, Gemini, Factory Droid, Devin, and Cursor only where supported by their documented extension interfaces. Keep each integration optional and separate from core packaging.
4. Store agent-generated commentary in a separate artifact with tool/model name, prompt version, timestamp, and human-review status. Never mutate deterministic scan outputs.
5. Document data transfer, model-provider controls, safe sharing, and opt-in behavior. Add tests for redaction and finding-ID citations.

### Phase 7 acceptance

- Core scan remains fully functional without an AI tool or network access.
- Generated commentary is traceable and cannot overwrite measured findings.

## 12. Phase 8 — Release readiness and maintenance

**Goal:** ship and maintain a reliable Windows/Linux release suitable for analyst handoff.

### Tasks

1. Run a compatibility matrix for supported Windows/Linux and Python versions, Unicode paths, CRLF, permissions, large repositories, shallow clones, and offline use. Add representative synthetic fixtures, not sensitive customer repositories.
2. Review path traversal, symlink behavior, subprocess timeouts, resource bounds, error redaction, report injection/Markdown escaping, and dependency licenses. Record review outcomes.
3. Build package artifacts reproducibly; add version/changelog policy, release workflow, checksums, installation and upgrade instructions. Sign artifacts only if release infrastructure supports it reliably.
4. Publish capability matrix: language detection vs metric support; platform integrations and required scopes; online/offline behavior; schema version compatibility.
5. Perform manual report review against a synthetic example and confirm every claim maps to evidence or an explicit inference label.
6. Define maintenance: analyzer accuracy/false-positive review, advisory database update cadence, API change monitoring, supported Python/platform policy, security report channel, schema deprecation process, and release cadence.
7. Update README with actual install, usage, limitations, and output examples. Remove placeholders only when implementation supports the stated behavior.

### Phase 8 acceptance

- Release builds and installs on Windows and Linux using documented steps.
- Security/privacy review and manual evidence review are complete.
- Maintenance owners and compatibility promises are documented.

## 13. Testing practices for every phase

- Use TDD for behavior: write a small failing test for the expected public behavior, implement the smallest change, then refactor.
- Keep unit tests focused on pure transformations, parsing boundaries, and model contracts. Use fixture repositories for discovery and integration behavior.
- CLI tests invoke the public command and inspect exit status and output artifacts; avoid testing private helper call sequences.
- Use recorded responses for API and advisory tests. No ordinary test contacts external services or requires real credentials.
- Add a regression test whenever a false positive or data-loss bug is found.
- Assert privacy properties explicitly: no secret values, tokens, absolute user paths, or source excerpts appear unless a documented opt-in says otherwise.
- Keep test fixtures synthetic and small; bound performance tests separately from ordinary CI.
- Required local check before each phase commit: formatter/linter, type checker, and full pytest suite. CI is authoritative across operating systems.

## 14. Commit and review cadence

Use frequent commits with a conventional, descriptive message, for example `feat(inventory): count physical and blank lines`. Each commit should leave the branch understandable and tests green. For a task requiring a broad interface change, first commit the contract and migration tests, then implementation. At each phase boundary, review the diff against acceptance criteria, update docs and phase summary if scope changed, and write a short phase completion note in the PR or commit description.

## 15. Definition of done for the initial MVP (end of Phase 2)

- A user can install and run CodeScan on Linux or Windows without credentials.
- `codescan scan PATH --output DIR` creates `report.md`, `files.csv`, and `results.json`.
- CSV rows include relative path, detected language, LOC, blank lines, and bytes; summaries reconcile with rows.
- The report states scope, skipped/unreadable inputs, analyzer statuses, and limitations.
- The default scan does not run target code, follow symlinks outside the root, or send data over the network.
- User-facing docs explain installation, invocation, output interpretation, and privacy limits.
- CI verifies the same contracts on both operating systems.

## 16. Next Steps — optional post-launch enhancements

- [Keith's idea] Expand the analyzer and integration set based on real engagement needs and analyst feedback.
- [Keith's idea] Add a secure, standardized export bundle for email and project data-room handoff.
- [Claude's idea] Add scan-to-scan comparison to highlight changes in architecture, tests, contributors, and dependency risk.
- [Claude's idea] Add configurable organization profiles for thresholds and report emphasis while retaining raw measurements and evidence.
