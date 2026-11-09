# Command-line interface

The initial package exposes `codescan --version` and `codescan scan PATH`. The scan subcommand validates that `PATH` exists and is a directory. Inventory and report generation are under development; the command currently returns a clear not-implemented status after validation.

```shell
codescan --version
codescan scan ./project --output ./codescan-output
```

The `--output` option is reserved for the Phase 2 output bundle. No target project code is executed.
