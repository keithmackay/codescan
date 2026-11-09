"""JSON renderer for normalized scan output."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from codescan import __version__
from codescan.analyzers.inventory import FileInventory


def render_results(root_label: str, items: Sequence[FileInventory], scan_id: str) -> str:
    payload = {
        "schema_version": "1.0",
        "scan_id": scan_id,
        "codescan_version": __version__,
        "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "root_label": root_label,
        "analyzers": [{"name": "inventory", "status": "completed"}],
        "findings": [],
        "files": [
            {
                "path": item.path,
                "language": item.language,
                "loc": item.loc,
                "blank_lines": item.blank_lines,
                "total_lines": item.total_lines,
                "bytes": item.bytes,
            }
            for item in items
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
