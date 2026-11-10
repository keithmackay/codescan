"""Discover test, documentation, and coverage artifacts without claiming execution."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from codescan.discovery import discover_files
from codescan.models import Evidence, Finding

TEST_DIRECTORY_NAMES = {"test", "tests", "spec", "specs"}
DOC_DIRECTORY_NAMES = {"docs", "documentation"}
DOC_FILENAMES = {"readme", "contributing", "architecture", "development"}
COVERAGE_FILENAMES = {"coverage.xml", "lcov.info", "cobertura.xml", "jacoco.xml"}


def analyze_tests_docs(root: Path) -> tuple[list[Finding], Literal["completed"]]:
    findings: list[Finding] = []
    entries = discover_files(root, include_hidden=True)
    test_evidence: list[Evidence] = []
    doc_evidence: list[Evidence] = []
    coverage_evidence: list[Evidence] = []

    for entry in entries:
        parts = Path(entry.relative_path).parts
        lower_parts = {part.lower() for part in parts}
        stem = Path(parts[-1]).stem.lower()
        if (
            lower_parts & TEST_DIRECTORY_NAMES
            or stem.startswith(("test_", "test.", "spec_", "spec."))
            or stem.endswith(("_test", ".test", "_spec", ".spec"))
        ):
            test_evidence.append(Evidence(kind="test_file", path=entry.relative_path))
        if lower_parts & DOC_DIRECTORY_NAMES or stem in DOC_FILENAMES:
            doc_evidence.append(Evidence(kind="documentation_file", path=entry.relative_path))
        if Path(parts[-1]).name.lower() in COVERAGE_FILENAMES:
            coverage_evidence.append(Evidence(kind="coverage_artifact", path=entry.relative_path))

    if test_evidence:
        findings.append(
            Finding(
                id="TESTS-DISCOVERED-001",
                category="testing",
                title="Tests detected",
                summary=f"Detected {len(test_evidence)} file(s) or path(s) matching common test naming conventions; execution and coverage were not measured.",
                evidence=test_evidence,
                limitations=["Naming conventions may miss tests or include non-test files."],
            )
        )
    else:
        findings.append(
            Finding(
                id="TESTS-NOTDETECTED-001",
                category="testing",
                title="Tests not detected",
                summary="Tests were not detected from common file and directory naming conventions; this is not evidence that tests do not exist.",
                limitations=[
                    "Only conventional local paths and filenames are checked; test discovery varies by language and build system."
                ],
            )
        )
    if doc_evidence:
        findings.append(
            Finding(
                id="DOCS-DISCOVERED-001",
                category="documentation",
                title="Project documentation detected",
                summary=f"Detected {len(doc_evidence)} documentation file(s) or paths by common naming conventions.",
                evidence=doc_evidence,
                limitations=["Presence does not measure completeness, accuracy, or freshness."],
            )
        )
    else:
        findings.append(
            Finding(
                id="DOCS-NOTDETECTED-001",
                category="documentation",
                title="Project documentation not detected",
                summary="Common documentation files and directories were not detected; documentation may exist elsewhere.",
                limitations=["Only conventional local names and paths are checked."],
            )
        )
    if coverage_evidence:
        findings.append(
            Finding(
                id="COVERAGE-ARTIFACT-001",
                category="testing",
                title="Coverage artifact detected",
                summary=f"Detected {len(coverage_evidence)} coverage artifact(s); coverage percentages were not parsed.",
                evidence=coverage_evidence,
                limitations=[
                    "Artifact presence does not establish freshness, completeness, or measured coverage."
                ],
            )
        )
    return findings, "completed"
