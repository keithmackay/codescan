# Output schema (MVP)

Each scan writes three UTF-8 files. A scan with developer identity encryption also writes a separate encrypted identity map.

- `report.md`: project label, scan scope (hidden-file setting, explicit excludes, default ignored directories, and symlink behavior), file/LOC totals, per-language totals, findings (including discovered files omitted due to read errors), parsed coverage percentages when supported artifacts supply line totals, dependency/vulnerability summaries, optional package license evidence, analyzer statuses, and limitations.
- `files.csv`: stable columns `path`, `language`, `loc`, `blank_lines`, and `bytes`, sorted by relative path.
- `results.json`: schema version `1.0`, scan ID, CodeScan version, UTC start time, root label, scan scope, analyzer statuses, findings, dependencies, optional vulnerability and package license results, and per-file inventory including total physical lines.
- `developer-identities.enc.json` (opt-in): authenticated encrypted mapping from pseudonymous developer IDs to names/emails and activity data. Names/emails do not appear in the Markdown/JSON report.

LOC currently means nonblank physical lines. It is not comment-aware and does not measure executable statements. Language is inferred only from filename extension; unknown extensions remain `unknown`. Unreadable discovered files are excluded from CSV and totals and named in a finding with partial inventory status. Absolute scan paths and file contents are not written to these artifacts.

Project-controlled strings are Markdown-escaped in `report.md`; normalized evidence values remain unchanged in `results.json`.

Vulnerability results are absent when scanning is disabled or incomplete; check analyzer status to distinguish those cases from a completed scan with no findings. Online OSV scans require explicit opt-in.

Dependency records include `source_path` for a primary manifest and `source_paths` for all manifests that contributed the same ecosystem/package/version/version-kind record.
