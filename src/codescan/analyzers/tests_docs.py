"""Discover test, documentation, and coverage artifacts without claiming execution."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from codescan.discovery import discover_files
from codescan.models import Evidence, Finding

TEST_DIRECTORY_NAMES = {"test", "tests", "spec", "specs"}
DOC_DIRECTORY_NAMES = {"docs", "documentation"}
DOC_FILENAMES = {"readme", "contributing", "architecture", "development"}
COVERAGE_FILENAMES = {"coverage.xml", "lcov.info", "cobertura.xml", "jacoco.xml"}
MAX_COVERAGE_ARTIFACT_BYTES = 10 * 1024 * 1024


def _coverage_totals(path: Path) -> tuple[int, int] | None:
    if path.name.lower() == "lcov.info":
        covered = total = 0
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("LH:"):
                covered += int(line[3:])
            elif line.startswith("LF:"):
                total += int(line[3:])
        return (covered, total) if total else None

    root = ET.parse(path).getroot()
    if root.tag.rsplit("}", 1)[-1] == "report":  # JaCoCo
        for counter in root.findall(".//counter"):
            if counter.attrib.get("type") == "LINE":
                missed = int(counter.attrib["missed"])
                covered = int(counter.attrib["covered"])
                return covered, missed + covered
        return None

    if root.tag.rsplit("}", 1)[-1] == "coverage":  # Cobertura
        covered_attr = root.attrib.get("lines-covered")
        total_attr = root.attrib.get("lines-valid")
        if covered_attr is not None and total_attr is not None:
            return int(covered_attr), int(total_attr)
        return None
    return None


def analyze_tests_docs(root: Path) -> tuple[list[Finding], Literal["completed", "partial"]]:
    findings: list[Finding] = []
    entries = discover_files(root, include_hidden=True)
    test_evidence: list[Evidence] = []
    doc_evidence: list[Evidence] = []
    coverage_evidence: list[Evidence] = []
    coverage_errors = False
    parsed_coverage_count = 0

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
            try:
                if entry.path.stat().st_size > MAX_COVERAGE_ARTIFACT_BYTES:
                    raise ValueError("artifact exceeds size limit")
                totals = _coverage_totals(entry.path)
                if totals is None or totals[1] <= 0 or totals[0] < 0 or totals[0] > totals[1]:
                    coverage_evidence.append(
                        Evidence(
                            kind="coverage_artifact",
                            path=entry.relative_path,
                            detail="line percentage unavailable",
                        )
                    )
                    coverage_errors = True
                else:
                    covered, total = totals
                    percent = covered / total * 100
                    coverage_evidence.append(
                        Evidence(
                            kind="coverage_artifact",
                            path=entry.relative_path,
                            detail=f"{covered}/{total} lines ({percent:.1f}%)",
                        )
                    )
                    parsed_coverage_count += 1
            except (OSError, ValueError, KeyError, ET.ParseError):
                coverage_evidence.append(
                    Evidence(
                        kind="coverage_artifact",
                        path=entry.relative_path,
                        detail="line percentage unavailable",
                    )
                )
                coverage_errors = True

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
                summary=(
                    f"Parsed line coverage from {parsed_coverage_count} "
                    f"of {len(coverage_evidence)} artifact(s); "
                    + ", ".join(
                        evidence.detail
                        for evidence in coverage_evidence
                        if evidence.detail and "(" in evidence.detail
                    )
                    + ("; " if not coverage_errors and coverage_evidence else "")
                    + (
                        "one or more percentages are unavailable."
                        if coverage_errors
                        else "percentages reflect the supplied artifacts only."
                    )
                ),
                evidence=coverage_evidence,
                limitations=[
                    "Artifact presence does not establish freshness, completeness, or measured coverage."
                ],
            )
        )
    return findings, "partial" if coverage_errors else "completed"
