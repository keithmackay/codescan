"""Markdown report renderer."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from codescan.analyzers.inventory import FileInventory


def render_report(
    root_label: str, items: Sequence[FileInventory], limitations: Sequence[str] = ()
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
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in limitations)
    if not limitations:
        lines.append(
            "- This MVP reports file inventory only; quality analyzers are not yet available."
        )
    return "\n".join(lines) + "\n"
