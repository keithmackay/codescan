"""Markdown report renderer."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from html import escape

from codescan.analyzers.dependencies import Dependency
from codescan.analyzers.inventory import FileInventory
from codescan.analyzers.osv_scanner import PackageLicense, Vulnerability
from codescan.models import AnalyzerStatus, Finding, ScanScope


def _table_cell(value: str) -> str:
    return _escape_markdown(value)


def _prose(value: str) -> str:
    return _escape_markdown(value)


def _escape_markdown(value: str) -> str:
    normalized = escape(value.replace("\r", " ").replace("\n", " "), quote=False)
    escaped = re.sub(r"([\\`*_{}\[\]()!|])", r"\\\1", normalized)
    escaped = re.sub(r"^([ \t]{0,3})(#{1,6}|>|[-+*])(?=\s)", r"\1\\\2", escaped)
    return re.sub(r"^([ \t]{0,3}\d+)([.)])(?=\s)", r"\1\\\2", escaped)


def _inline_code(value: str) -> str:
    normalized = value.replace("\r", " ").replace("\n", " ")
    longest_run = max((len(run) for run in re.findall(r"`+", normalized)), default=0)
    delimiter = "`" * (longest_run + 1)
    return f"{delimiter}{normalized}{delimiter}"


def render_report(
    root_label: str,
    items: Sequence[FileInventory],
    limitations: Sequence[str] = (),
    findings: Sequence[Finding] = (),
    dependencies: Sequence[Dependency] = (),
    vulnerabilities: Sequence[Vulnerability] = (),
    analyzers: Sequence[AnalyzerStatus] = (),
    package_licenses: Sequence[PackageLicense] = (),
    scope: ScanScope | None = None,
) -> str:
    scan_scope = scope or ScanScope()
    language_counts = Counter(item.language for item in items)
    loc_total = sum(item.loc for item in items)
    lines = [
        "# CodeScan report",
        "",
        f"- Project: {_inline_code(root_label)}",
        f"- Files inventoried: {len(items)}",
        f"- Nonblank physical lines (LOC): {loc_total}",
        "",
        "## Scan scope",
        "",
        f"- Include hidden files: {'yes' if scan_scope.include_hidden else 'no'}",
        f"- Follow symlinks: {'yes' if scan_scope.follow_symlinks else 'no'}",
        "- User exclude patterns: "
        + (
            ", ".join(_inline_code(pattern) for pattern in scan_scope.exclude_patterns)
            if scan_scope.exclude_patterns
            else "none"
        ),
        "- Default ignored directories: "
        + (
            ", ".join(_inline_code(name) for name in scan_scope.default_ignored_directories)
            if scan_scope.default_ignored_directories
            else "none"
        ),
        "",
        "## Language inventory",
        "",
        "| Language | Files | LOC |",
        "|---|---:|---:|",
    ]
    for language, count in sorted(language_counts.items(), key=lambda pair: pair[0].casefold()):
        language_loc = sum(item.loc for item in items if item.language == language)
        lines.append(f"| {_table_cell(language)} | {count} | {language_loc} |")
    lines.extend(["", "## Findings", ""])
    if findings:
        for finding in findings:
            lines.extend([f"### {_prose(finding.title)}", "", _prose(finding.summary), ""])
            for evidence in finding.evidence:
                location = _inline_code(evidence.path) if evidence.path else _prose(evidence.kind)
                detail = f" — {_prose(evidence.detail)}" if evidence.detail else ""
                lines.append(f"- Evidence: {location}{detail}")
            for limitation in finding.limitations:
                lines.append(f"- Limitation: {_prose(limitation)}")
            lines.append("")
    else:
        lines.append("No findings were produced by the enabled analyzers.")
    lines.extend(["", "## Dependency inventory", ""])
    if dependencies:
        lines.extend(["| Ecosystem | Packages |", "|---|---:|"])
        ecosystem_counts = Counter(dependency.ecosystem for dependency in dependencies)
        lines.extend(
            f"| {_table_cell(ecosystem)} | {count} |"
            for ecosystem, count in sorted(ecosystem_counts.items())
        )
        lines.append("")
        lines.append(
            "CodeScan extracted these dependency records locally from supported manifests."
        )
    else:
        lines.append("No dependencies were extracted from supported manifests.")
    lines.extend(["", "## Known vulnerability results", ""])
    if vulnerabilities:
        lines.extend(
            [
                "| Advisory | Package | Version | Severity | Fixed version(s) | Advisory updated | Source |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for item in vulnerabilities:
            advisory = (
                f"[{item.advisory_id}](https://osv.dev/{item.advisory_id})"
                if re.fullmatch(r"[A-Za-z0-9._-]+", item.advisory_id)
                else _table_cell(item.advisory_id)
            )
            fixed = _table_cell(", ".join(item.fixed_versions) or "Not provided")
            source = _table_cell(item.source_path or "Not provided")
            lines.append(
                f"| {advisory} | {_table_cell(item.ecosystem + ':' + item.package)} | "
                f"{_table_cell(item.version)} | {_table_cell(item.severity or 'Not provided')} | "
                f"{fixed} | {_table_cell(item.modified or 'Not provided')} | {source} |"
            )
        lines.append("")
    else:
        lines.append(
            "No vulnerability results are available; see analyzer status for whether scanning was disabled or incomplete."
        )
    lines.extend(["", "## Analyzer status", "", "| Analyzer | Status | Details |", "|---|---|---|"])
    for analyzer in analyzers:
        detail = _table_cell(analyzer.message or "")
        lines.append(
            f"| {_table_cell(analyzer.name)} | {_table_cell(analyzer.status)} | {detail} |"
        )
    lines.extend(["", "## Dependency license evidence", ""])
    if package_licenses:
        lines.extend(["| Package | Version | License(s) | Source |", "|---|---|---|---|"])
        for package_license in package_licenses:
            source_path = _table_cell(package_license.source_path or "Not provided")
            licenses = _table_cell(", ".join(package_license.licenses) or "Unknown")
            lines.append(
                f"| {_table_cell(package_license.ecosystem + ':' + package_license.package)} | "
                f"{_table_cell(package_license.version)} | {licenses} | {source_path} |"
            )
            if package_license.violations:
                lines.append(
                    f"| **Reported allowlist violation(s)** |  | "
                    f"{_table_cell(', '.join(package_license.violations))} | Review SPDX policy |"
                )
        lines.append("")
        lines.append(
            "License identifiers are evidence for human/legal review, not a legal risk determination."
        )
    else:
        lines.append(
            "No package license lookup results are available; this feature is opt-in and requires online OSV-Scanner mode."
        )
    lines.extend(["", "## Project license files", ""])
    project_license_findings = [finding for finding in findings if finding.category == "licensing"]
    if project_license_findings:
        for finding in project_license_findings:
            lines.append(f"- **{_prose(finding.title)}:** {_prose(finding.summary)}")
            if finding.evidence:
                lines.append(
                    "  - Files: "
                    + ", ".join(
                        _table_cell(evidence.path or evidence.detail or "Unknown")
                        for evidence in finding.evidence
                    )
                )
    else:
        lines.append("No project license file assessment was produced.")
    lines.append("Presence only; CodeScan does not interpret the terms or make a legal conclusion.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {_prose(limitation)}" for limitation in limitations)
    if not limitations:
        lines.append(
            "- Findings are heuristic indicators and should be reviewed with project context."
        )
    return "\n".join(lines) + "\n"
