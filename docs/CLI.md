# Command-line interface

```shell
codescan --version
codescan scan PATH [--output DIR] [--exclude PATTERN] [--include-hidden] [--force]
```

A scan writes `report.md`, `files.csv`, and `results.json`. By default the output directory is `PATH/codescan-output`; use `--output` to choose another location. Existing report artifacts are protected unless `--force` is supplied. Repeat `--exclude` to omit matching relative path patterns. Hidden files and folders are excluded by default; `--include-hidden` includes them.

CodeScan skips common generated/vendor folders and does not follow symlinks. It does not execute target project code or make network requests. The MVP currently measures file inventory only; quality analyzers and platform integrations are not yet available.
