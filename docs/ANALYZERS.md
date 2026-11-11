# Analyzer definitions and limitations

## Current analyzers

| Analyzer | Signal | Evidence | Important limitation |
|---|---|---|---|
| Inventory | Extension-derived language, bytes, nonblank physical lines, blank lines | Relative file path and measured counts; unreadable discovered paths are reported | Unreadable files are omitted from CSV and totals, with partial analyzer status; LOC is not comment-aware; unknown extensions stay unknown. |
| Repository hygiene | TODO/FIXME marker counts, likely secret filenames, files above 1 MB | Relative path and count/size only | Heuristic indicators; file contents and secret values are not included in findings. |
| Tests and documentation | Conventional test and documentation names; line totals from Cobertura, LCOV, and JaCoCo coverage artifacts | Relative path, covered/total lines, percentage when parseable | Does not run tests or establish artifact freshness/completeness; malformed or unsupported coverage artifacts yield partial status. |
| Git history | Commit count, author-account concentration, local date range, and shallow-history status | Aggregate counts and repository state | Names/emails are omitted; aliases are not merged; counts do not measure quality or productivity. |
| Developer activity (opt-in) | Commits, files changed, additions, and deletions grouped by seed-scoped developer ID | Pseudonymous ID and aggregate activity; identity map is encrypted separately | Requires user seed; raw names/emails only appear in encrypted map; Git aliases are not merged. |
| Process artifacts | CI/CD, CODEOWNERS, pull request template, and contribution configuration files | Relative path | Presence does not prove configuration is active or followed. |
| Complexity | Python AST cyclomatic complexity, physical function length, and nested control-flow depth | Function name, relative path, line number, and measured values | Python only; thresholds are review prompts. Function length includes blank/comment lines and the definition line; unsupported languages are not measured. |
| Dependency inventory | Static parsing of requirements, package-lock, go.mod, pyproject/Poetry, Composer, Gemfile.lock, Maven, and NuGet project files | Relative manifest path, package name, version/constraint, ecosystem | No package manager is run; unsupported formats and unbounded Python requirements may not yield entries. |
| Project license files | Presence of common root-level LICENSE, COPYING, and NOTICE names | Relative filename | Does not identify actual terms or determine legal risk. |
| Vulnerability lookup (opt-in) | OSV-Scanner JSON findings with aliases, ecosystem/package/version, fixed versions, severity when supplied, and source path | Advisory IDs, package coordinates, relative source file, scanner version/mode | Disabled by default. Offline mode requires cached data; online mode sends dependency metadata to OSV.dev. |
| Package license lookup (opt-in) | OSV-Scanner license identifiers and allowlist violations | Package coordinates, identifiers, relative manifest path | Requires online mode and deps.dev; identifiers require human/legal review. |

Signals are descriptive prompts for human review. Absence of a detected artifact does not establish that a practice or artifact is absent. No aggregate quality score is calculated.

Analyzer exceptions are recorded as `failed` with the exception type only; the scan continues and includes results from analyzers that completed. Error messages and tracebacks are not copied into reports.

See [Dependency analyzer coverage](DEPENDENCIES.md) for the supported manifest matrix and parser limits.
