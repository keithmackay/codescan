# Development

## Requirements

- Python 3.11 or newer
- Git

## Setup

```shell
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
```

## Checks

```shell
ruff check .
ruff format --check .
mypy src
pytest
```

Tests should cover public behavior and metric boundaries. Keep ordinary tests offline and use small synthetic fixtures. Write a failing test before implementation, then run the focused test and the full suite before committing.
