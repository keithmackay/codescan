"""Safe local file discovery and deterministic extension-based language mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "codescan-output",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
}
LANGUAGE_EXTENSIONS = {
    ".cs": "C#",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".c": "C/C++",
    ".h": "C/C++",
    ".cc": "C/C++",
    ".hh": "C/C++",
    ".cpp": "C/C++",
    ".hpp": "C/C++",
    ".cxx": "C/C++",
    ".hxx": "C/C++",
    ".go": "Go",
    ".py": "Python",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sql": "SQL",
}


@dataclass(frozen=True)
class DiscoveredFile:
    path: Path
    relative_path: str


def detect_language(filename: str | Path) -> str:
    return LANGUAGE_EXTENSIONS.get(Path(filename).suffix.lower(), "unknown")


def discover_files(
    root: Path, excludes: tuple[str, ...] = (), include_hidden: bool = False
) -> list[DiscoveredFile]:
    root = root.resolve(strict=True)
    found: list[DiscoveredFile] = []
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if name not in IGNORED_DIRECTORIES
            and not name.endswith(".egg-info")
            and (include_hidden or not name.startswith("."))
            and not (current_path / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            if not include_hidden and any(part.startswith(".") for part in Path(relative).parts):
                continue
            if any(Path(relative).match(pattern) for pattern in excludes):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            found.append(DiscoveredFile(path=path, relative_path=relative))
    return sorted(found, key=lambda item: item.relative_path.casefold())
