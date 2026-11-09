"""CSV renderer for file inventory."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from codescan.analyzers.inventory import FileInventory


def render_inventory_csv(items: Iterable[FileInventory]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["path", "language", "loc", "blank_lines", "bytes"])
    for item in sorted(items, key=lambda row: row.path.casefold()):
        writer.writerow([item.path, item.language, item.loc, item.blank_lines, item.bytes])
    return buffer.getvalue()
