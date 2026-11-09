"""Per-file inventory metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from codescan.discovery import detect_language


@dataclass(frozen=True)
class FileInventory:
    path: str
    language: str
    loc: int
    blank_lines: int
    total_lines: int
    bytes: int


def inventory_file(path: Path, root: Path) -> FileInventory:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    blank_lines = sum(not line.strip() for line in lines)
    return FileInventory(
        path=path.relative_to(root).as_posix(),
        language=detect_language(path.name),
        loc=len(lines) - blank_lines,
        blank_lines=blank_lines,
        total_lines=len(lines),
        bytes=len(data),
    )


def inventory_dict(item: FileInventory) -> dict[str, object]:
    return asdict(item)
