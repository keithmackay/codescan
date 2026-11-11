"""Safe local file discovery and deterministic extension-based language mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cache
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


def _matches_exclude(relative_path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/").strip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return False
    path_parts = relative_path.split("/")
    pattern_parts = normalized.split("/")
    if len(pattern_parts) == 1:
        return any(fnmatchcase(part, pattern_parts[0]) for part in path_parts)

    @cache
    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        if pattern_parts[pattern_index] == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_parts)
            and fnmatchcase(path_parts[path_index], pattern_parts[pattern_index])
            and match(path_index + 1, pattern_index + 1)
        )

    return match(0, 0)


def detect_language(filename: str | Path) -> str:
    return LANGUAGE_EXTENSIONS.get(Path(filename).suffix.lower(), "unknown")


def discover_files(
    root: Path, excludes: tuple[str, ...] = (), include_hidden: bool = False
) -> list[DiscoveredFile]:
    root = root.resolve(strict=True)
    found: list[DiscoveredFile] = []
    normalized_excludes = tuple(pattern for pattern in excludes if pattern)
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        current_relative = current_path.relative_to(root).as_posix()
        directories[:] = sorted(
            name
            for name in directories
            if name not in IGNORED_DIRECTORIES
            and not name.endswith(".egg-info")
            and (include_hidden or not name.startswith("."))
            and not (current_path / name).is_symlink()
            and not any(
                _matches_exclude(
                    name if current_relative == "." else f"{current_relative}/{name}", pattern
                )
                for pattern in normalized_excludes
            )
        )
        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            if not include_hidden and any(part.startswith(".") for part in Path(relative).parts):
                continue
            if any(_matches_exclude(relative, pattern) for pattern in normalized_excludes):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            found.append(DiscoveredFile(path=path, relative_path=relative))
    return sorted(found, key=lambda item: item.relative_path.casefold())
