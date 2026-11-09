import json
from datetime import UTC, datetime

from codescan.models import AnalyzerStatus, Evidence, Finding, ScanResult, serialize_result


def test_result_serializes_versioned_contract():
    result = ScanResult(
        scan_id="scan-1",
        codescan_version="0.1.0",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        root_label="sample-project",
        analyzers=[AnalyzerStatus(name="inventory", status="completed")],
        findings=[
            Finding(
                id="INV-001",
                category="inventory",
                title="Example",
                summary="Example finding",
                evidence=[Evidence(kind="file", path="src/main.py")],
            )
        ],
    )

    payload = json.loads(serialize_result(result))
    assert payload["schema_version"] == "1.0"
    assert payload["scan_id"] == "scan-1"
    assert payload["analyzers"][0]["status"] == "completed"
    assert payload["findings"][0]["evidence"][0]["path"] == "src/main.py"


def test_analyzer_status_rejects_unknown_state():
    try:
        AnalyzerStatus(name="inventory", status="unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown analyzer status must be rejected")
