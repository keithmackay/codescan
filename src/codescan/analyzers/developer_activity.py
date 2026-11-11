"""Seed-protected developer activity grouped by pseudonymous IDs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Literal

from codescan.identity_crypto import developer_id
from codescan.models import Evidence, Finding


def analyze_developer_activity(
    root: Path, seed: str
) -> tuple[
    list[Finding], dict[str, dict[str, str | int]], Literal["completed", "partial", "skipped"]
]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%an%x1f%ae%x1f%aI", "--numstat"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [], {}, "partial"
    if result.returncode:
        return [], {}, "skipped"

    authors: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in result.stdout.splitlines():
        if "\x1f" in line:
            parts = line.split("\x1f", 2)
            if len(parts) == 3:
                name, email, authored_at = parts
                identifier = developer_id(name, email, seed)
                current = authors.setdefault(
                    identifier,
                    {
                        "name": name,
                        "email": email,
                        "commits": 0,
                        "additions": 0,
                        "deletions": 0,
                        "files_changed": 0,
                        "first_seen": authored_at,
                        "last_seen": authored_at,
                    },
                )
                current["commits"] += 1
                current["first_seen"] = min(current["first_seen"], authored_at)
                current["last_seen"] = max(current["last_seen"], authored_at)
        elif current is not None and "\t" in line:
            fields = line.split("\t", 2)
            if len(fields) == 3:
                added, removed, _filename = fields
                if added.isdigit():
                    current["additions"] += int(added)
                if removed.isdigit():
                    current["deletions"] += int(removed)
                current["files_changed"] += 1

    total_commits = sum(int(author["commits"]) for author in authors.values())
    identity_map: dict[str, dict[str, str | int]] = {}
    activity_rows: list[str] = []
    for identifier, author in sorted(authors.items()):
        commits = int(author["commits"])
        share = commits / total_commits if total_commits else 0
        activity_rows.append(
            f"{identifier}: {commits} commit(s), {share:.0%} of activity, "
            f"{author['files_changed']} file change(s), +{author['additions']}/-{author['deletions']} lines"
        )
        identity_map[identifier] = {
            "name": str(author["name"]),
            "email": str(author["email"]),
            "commits": commits,
            "files_changed": int(author["files_changed"]),
            "additions": int(author["additions"]),
            "deletions": int(author["deletions"]),
        }
    if not authors:
        return [], {}, "completed"

    finding = Finding(
        id="GIT-DEVELOPER-ACTIVITY-001",
        category="developer_activity",
        title="Developer activity by pseudonymous ID",
        summary="Detailed local Git activity is grouped by seed-scoped pseudonymous IDs.",
        evidence=[Evidence(kind="developer_activity", detail=row) for row in activity_rows],
        limitations=[
            "Commit and line-change counts do not measure productivity, code quality, or individual contribution value.",
            "Identity grouping depends on exact author name/email pairs; aliases are not merged automatically.",
            "Only locally available Git history is included; shallow clones may omit activity.",
        ],
    )
    return [finding], identity_map, "completed"
