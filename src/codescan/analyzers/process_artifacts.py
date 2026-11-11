"""Detect repository files that describe or configure development processes."""

from __future__ import annotations

from pathlib import Path

from codescan.discovery import discover_files
from codescan.models import Evidence, Finding

PROCESS_FILENAMES = {
    "codeowners",
    "pull_request_template.md",
    "pull_request_template",
    "contributing.md",
    "azure-pipelines.yml",
    "azure-pipelines.yaml",
    "jenkinsfile",
    ".gitlab-ci.yml",
}
PROCESS_PATH_MARKERS = (
    ".github/workflows/",
    ".github/pull_request_template",
    ".azure/pipelines/",
    ".circleci/",
    ".buildkite/",
    ".teamcity/",
)


def analyze_process_artifacts(root: Path) -> list[Finding]:
    evidence: list[Evidence] = []
    for entry in discover_files(root, include_hidden=True):
        relative = entry.relative_path.lower()
        filename = Path(relative).name
        if filename in PROCESS_FILENAMES or any(
            marker in relative for marker in PROCESS_PATH_MARKERS
        ):
            evidence.append(Evidence(kind="process_configuration", path=entry.relative_path))
    if not evidence:
        return []
    return [
        Finding(
            id="PROCESS-ARTIFACTS-001",
            category="process_evidence",
            title="Process configuration artifacts detected",
            summary=f"Detected {len(evidence)} file(s) commonly used to configure CI/CD, ownership, or contribution workflows.",
            evidence=evidence,
            limitations=[
                "Configuration artifacts do not prove that the process is enabled, followed, or effective."
            ],
        )
    ]
