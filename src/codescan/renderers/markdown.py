"""Markdown report renderer."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from codescan.analyzers.inventory import FileInventory
from codescan.models import Finding


def render_report(
    root_label: str,
    items: Sequence[FileInventory],
    limitations: Sequence[str] = (),
    findings: Sequence[Finding] = (),
) -> str:
    language_counts = Counter(item.language for item in items)
    loc_total = sum(item.loc for item in items)
    lines = [
        "# CodeScan report",
        "",
        f"- Project: `{root_label}`",
        f"- Files inventoried: {len(items)}",
        f"- Nonblank physical lines (LOC): {loc_total}",
        "",
        "## Language inventory",
        "",
        "| Language | Files | LOC |",
        "|---|---:|---:|",
    ]
    for language, count in sorted(language_counts.items(), key=lambda pair: pair[0].casefold()):
        language_loc = sum(item.loc for item in items if item.language == language)
        lines.append(f"| {language} | {count} | {language_loc} |")
    lines.extend(["", "## Findings", ""])
    if findings:
        for finding in findings:
            lines.extend([f"### {finding.title}", "", finding.summary, ""])
            for evidence in finding.evidence:
                location = f"`{evidence.path}`" if evidence.path else evidence.kind
                detail = f" — {evidence.detail}" if evidence.detail else ""
                lines.append(f"- Evidence: {location}{detail}")
            for limitation in finding.limitations:
                lines.append(f"- Limitation: {limitation}")
            lines.append("")
    else:
        lines.append("No findings were produced by the enabled analyzers.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in limitations)
    if not limitations:
        lines.append(
            "- Findings are heuristic indicators and should be reviewed with project context."
        )
    return "\n".join(lines) + "\n"
