"""Simple repository hygiene signals with file-based evidence."""

from __future__ import annotations

from pathlib import Path

from codescan.discovery import discover_files
from codescan.models import Evidence, Finding

SECRET_FILENAMES = {".env", ".env.local", "id_rsa", "id_dsa", "credentials.json", "secrets.yml"}


def analyze_repository(root: Path, large_file_threshold: int = 1_000_000) -> list[Finding]:
    findings: list[Finding] = []
    todo_files: list[tuple[str, int]] = []
    oversized: list[tuple[str, int]] = []
    secret_files: list[str] = []

    for entry in discover_files(root, include_hidden=True):
        name = Path(entry.relative_path).name.lower()
        if name in SECRET_FILENAMES or (name.startswith(".env.") and name != ".env.example"):
            secret_files.append(entry.relative_path)
        try:
            size = entry.path.stat().st_size
            if size > large_file_threshold:
                oversized.append((entry.relative_path, size))
            content = entry.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        marker_count = sum(
            1 for line in content.splitlines() if "TODO" in line.upper() or "FIXME" in line.upper()
        )
        if marker_count:
            todo_files.append((entry.relative_path, marker_count))

    if todo_files:
        count = sum(total for _, total in todo_files)
        findings.append(
            Finding(
                id="REPO-TODO-001",
                category="repository_hygiene",
                title="TODO/FIXME markers detected",
                summary=f"Found {count} TODO/FIXME marker(s) across {len(todo_files)} file(s).",
                evidence=[
                    Evidence(kind="marker_count", path=path, detail=f"{total} marker(s)")
                    for path, total in todo_files
                ],
                limitations=[
                    "Markers may be examples or intentionally deferred work; review context manually."
                ],
            )
        )
    if secret_files:
        findings.append(
            Finding(
                id="REPO-SECRETFILE-001",
                category="repository_hygiene",
                title="Potential secrets file detected",
                summary=f"Found {len(secret_files)} file(s) with names commonly used for local secrets.",
                evidence=[Evidence(kind="filename", path=path) for path in secret_files],
                limitations=[
                    "Filename detection does not inspect values or confirm that secrets are present."
                ],
            )
        )
    if oversized:
        findings.append(
            Finding(
                id="REPO-LARGEFILE-001",
                category="repository_hygiene",
                title="Large files detected",
                summary=f"Found {len(oversized)} file(s) larger than {large_file_threshold} bytes.",
                evidence=[
                    Evidence(kind="file_size", path=path, detail=f"{size} bytes")
                    for path, size in oversized
                ],
                limitations=[
                    "Large files may be generated assets or intentional data; size alone is not a quality defect."
                ],
            )
        )
    return findings
