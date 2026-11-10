# Analyzer definitions and limitations

## Current analyzers

| Analyzer | Signal | Evidence | Important limitation |
|---|---|---|---|
| Inventory | Extension-derived language, bytes, nonblank physical lines, blank lines | Relative file path and measured counts | LOC is not comment-aware; unknown extensions stay unknown. |
| Repository hygiene | TODO/FIXME marker counts, likely secret filenames, files above 1 MB | Relative path and count/size only | Heuristic indicators; file contents and secret values are not included in findings. |
| Tests and documentation | Conventional test and documentation names; common coverage artifact filenames | Relative path | Does not run tests, measure coverage, or assess documentation quality. |
| Complexity | Skipped | None | Not yet implemented. |
| Dependency risk | Skipped | None | Not yet implemented; no online checks are run. |

Signals are descriptive prompts for human review. Absence of a detected artifact does not establish that a practice or artifact is absent. No aggregate quality score is calculated.
