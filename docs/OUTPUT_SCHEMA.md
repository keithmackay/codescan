# Output schema (MVP)

Each scan writes three UTF-8 files:

- `report.md`: project label, file/LOC totals, per-language totals, and current analyzer limitations.
- `files.csv`: stable columns `path`, `language`, `loc`, `blank_lines`, and `bytes`, sorted by relative path.
- `results.json`: schema version `1.0`, scan ID, CodeScan version, UTC start time, root label, analyzer status, findings, and per-file inventory including total physical lines.

LOC currently means nonblank physical lines. It is not comment-aware and does not measure executable statements. Language is inferred only from filename extension; unknown extensions remain `unknown`. Absolute scan paths and file contents are not written to these artifacts.
