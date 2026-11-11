"""Read-only local Git activity and contributor-concentration signals."""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Literal

from codescan.models import Evidence, Finding


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def analyze_git_history(
    root: Path,
) -> tuple[list[Finding], Literal["completed", "partial", "skipped"]]:
    try:
        check = _git(root, "rev-parse", "--is-inside-work-tree")
        if check.returncode or check.stdout.strip() != "true":
            return [], "skipped"
        history = _git(root, "log", "--format=%an%x1f%aI")
        shallow = _git(root, "rev-parse", "--is-shallow-repository")
    except (OSError, subprocess.TimeoutExpired):
        return [], "partial"

    if history.returncode:
        return [], "partial"
    commits_by_author: Counter[str] = Counter()
    commit_dates: list[str] = []
    for line in history.stdout.splitlines():
        author, separator, authored_at = line.partition("\x1f")
        if separator:
            commits_by_author[author] += 1
            commit_dates.append(authored_at)
    if not commits_by_author:
        return [], "completed"

    total = sum(commits_by_author.values())
    top_share = max(commits_by_author.values()) / total
    shallow_history = shallow.returncode == 0 and shallow.stdout.strip() == "true"
    status: Literal["completed", "partial"] = "partial" if shallow_history else "completed"
    findings = [
        Finding(
            id="GIT-CONCENTRATION-001",
            category="contributor_concentration",
            title="Contributor activity concentration",
            summary=(
                f"The most active author accounts for {top_share:.0%} of {total} locally available commits "
                f"across {len(commits_by_author)} author account(s). Author identities are omitted by default."
            ),
            evidence=[
                Evidence(
                    kind="git_commit_summary",
                    detail=f"{total} commits; local date range {min(commit_dates)} to {max(commit_dates)}",
                )
            ],
            limitations=[
                "Commit counts do not measure productivity, code quality, or individual contribution value.",
                "Author aliases are not merged; shallow clones omit history.",
            ],
        )
    ]
    if shallow_history:
        findings.append(
            Finding(
                id="GIT-SHALLOW-001",
                category="history_coverage",
                title="Git history is shallow",
                summary="The local repository contains incomplete history; contributor measures may understate activity.",
                evidence=[
                    Evidence(kind="git_repository_state", detail="is-shallow-repository=true")
                ],
            )
        )
    return findings, status
