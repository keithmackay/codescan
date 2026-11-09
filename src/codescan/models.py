"""Versioned, serializable scan result models."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal

AnalyzerState = Literal["completed", "partial", "skipped", "failed"]


@dataclass(frozen=True)
class Evidence:
    kind: str
    path: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class AnalyzerStatus:
    name: str
    status: AnalyzerState
    message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"completed", "partial", "skipped", "failed"}:
            raise ValueError(f"unsupported analyzer status: {self.status}")


@dataclass(frozen=True)
class Finding:
    id: str
    category: str
    title: str
    summary: str
    severity: str | None = None
    confidence: str | None = None
    limitations: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class ScanResult:
    scan_id: str
    codescan_version: str
    started_at: datetime
    root_label: str
    analyzers: list[AnalyzerStatus] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    schema_version: str = "1.0"


def serialize_result(result: ScanResult) -> str:
    """Serialize a result to stable, human-readable JSON."""

    payload = asdict(result)
    payload["started_at"] = result.started_at.isoformat().replace("+00:00", "Z")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
