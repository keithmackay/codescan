"""JSON renderer for normalized scan output."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime

from codescan import __version__
from codescan.analyzers.dependencies import Dependency
from codescan.analyzers.inventory import FileInventory
from codescan.analyzers.osv_scanner import PackageLicense, Vulnerability
from codescan.models import AnalyzerStatus, Finding, ScanScope


def render_results(
    root_label: str,
    items: Sequence[FileInventory],
    scan_id: str,
    findings: Sequence[Finding] = (),
    analyzers: Sequence[AnalyzerStatus] = (),
    dependencies: Sequence[Dependency] = (),
    vulnerabilities: Sequence[Vulnerability] = (),
    package_licenses: Sequence[PackageLicense] = (),
    scope: ScanScope | None = None,
) -> str:
    payload = {
        "schema_version": "1.0",
        "scan_id": scan_id,
        "codescan_version": __version__,
        "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "root_label": root_label,
        "scope": asdict(scope or ScanScope()),
        "analyzers": [asdict(item) for item in analyzers]
        or [{"name": "inventory", "status": "completed"}],
        "findings": [asdict(item) for item in findings],
        "dependencies": [item.to_dict() for item in dependencies],
        "vulnerabilities": [item.to_dict() for item in vulnerabilities],
        "package_licenses": [item.to_dict() for item in package_licenses],
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
