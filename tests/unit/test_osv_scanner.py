import json
import subprocess

from codescan.analyzers.osv_scanner import normalize_osv_results, run_osv_scanner


def test_normalization_keeps_advisory_provenance_and_relative_paths(tmp_path):
    payload = {
        "results": [
            {
                "source": {"path": str(tmp_path / "requirements.txt"), "type": "lockfile"},
                "packages": [
                    {
                        "package": {"name": "requests", "version": "2.19.0", "ecosystem": "PyPI"},
                        "vulnerabilities": [
                            {
                                "id": "GHSA-test-1234-abcd",
                                "aliases": ["CVE-2025-0001"],
                                "summary": "Synthetic issue",
                                "affected": [{"ranges": [{"events": [{"fixed": "2.20.0"}]}]}],
                                "severity": [{"type": "CVSS_V3", "score": "8.1"}],
                                "modified": "2026-10-01T12:00:00Z",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    normalized = normalize_osv_results(payload, tmp_path)
    assert len(normalized) == 1
    result = normalized[0]
    assert result.advisory_id == "GHSA-test-1234-abcd"
    assert result.aliases == ["CVE-2025-0001"]
    assert result.fixed_versions == ["2.20.0"]
    assert result.severity == "CVSS_V3: 8.1"
    assert result.modified == "2026-10-01T12:00:00Z"
    assert result.source_path == "requirements.txt"
    assert str(tmp_path) not in json.dumps(result.to_dict())


def test_normalization_sanitizes_paths_outside_scan_root(tmp_path):
    payload = {
        "results": [
            {
                "source": {"path": "../../sensitive/project/package-lock.json"},
                "packages": [
                    {
                        "package": {"name": "pkg", "version": "1.0", "ecosystem": "npm"},
                        "vulnerabilities": [{"id": "GHSA-test-1234-abcd"}],
                    }
                ],
            }
        ]
    }
    result = normalize_osv_results(payload, tmp_path)[0]
    assert result.source_path == "package-lock.json"


def test_osv_runner_uses_offline_flag_and_never_runs_fix(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "osv-scanner 2.0.0", "")
        return subprocess.CompletedProcess(command, 0, '{"results": []}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_osv_scanner(tmp_path, mode="offline")
    assert result.status == "completed"
    assert "--offline" in calls[-1]
    assert "fix" not in calls[-1]
    assert "fix" not in " ".join(calls[-1])


def test_missing_scanner_is_skipped_not_zero_vulnerability_claim(tmp_path, monkeypatch):
    def missing(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    result = run_osv_scanner(tmp_path, executable="missing-osv-scanner", mode="online")
    assert result.status == "skipped"
    assert result.vulnerabilities == []
    assert "not installed" in (result.message or "")


def test_invalid_json_or_nonresult_exit_is_partial(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "osv-scanner 2.0", "")
        return subprocess.CompletedProcess(command, 2, "not json", "internal error")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_osv_scanner(tmp_path, mode="online")
    assert result.status == "partial"
    assert result.vulnerabilities == []


def test_online_mode_is_only_selected_explicitly_and_accepts_findings_exit(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "osv-scanner 2.1.0", "")
        return subprocess.CompletedProcess(command, 1, '{"results": []}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_osv_scanner(tmp_path, mode="online")
    assert result.status == "completed"
    assert "--offline" not in calls[-1]
    assert result.scanner_version == "2.1.0"


def test_license_normalization_preserves_package_and_license_evidence(tmp_path):
    from codescan.analyzers.osv_scanner import normalize_osv_licenses

    payload = {
        "results": [
            {
                "source": {"path": str(tmp_path / "package-lock.json")},
                "packages": [
                    {
                        "package": {"name": "example", "version": "1.2.0", "ecosystem": "npm"},
                        "licenses": ["MIT", "Apache-2.0"],
                        "license_violations": ["GPL-3.0-only"],
                    }
                ],
            }
        ]
    }
    results = normalize_osv_licenses(payload, tmp_path)
    assert results[0].licenses == ["Apache-2.0", "MIT"]
    assert results[0].violations == ["GPL-3.0-only"]
    assert results[0].source_path == "package-lock.json"


def test_license_scan_is_rejected_without_explicit_online_mode(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="online mode"):
        run_osv_scanner(tmp_path, mode="offline", include_licenses=True)


def test_license_mode_adds_explicit_scanner_option(tmp_path, monkeypatch):
    import subprocess

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "osv-scanner 2.0.0", "")
        return subprocess.CompletedProcess(command, 0, '{"results": []}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_osv_scanner(tmp_path, mode="online", include_licenses=True)
    assert "--licenses" in calls[-1]
    assert result.status == "completed"


def test_package_license_evidence_reaches_scan_artifacts(tmp_path, monkeypatch):
    from codescan.analyzers.osv_scanner import OsvScanResult, PackageLicense
    from codescan.scan import write_scan

    license_result = PackageLicense(
        package="example",
        ecosystem="npm",
        version="1.0.0",
        licenses=["MIT"],
        violations=[],
        source_path="package-lock.json",
    )
    monkeypatch.setattr(
        "codescan.scan.run_osv_scanner",
        lambda *_args, **_kwargs: OsvScanResult(
            "completed", "online", "2.0.0", licenses=[license_result]
        ),
    )
    output = tmp_path / "output"
    write_scan(tmp_path, output, vulnerability_mode="online", include_package_licenses=True)
    import json

    results = json.loads((output / "results.json").read_text(encoding="utf-8"))
    report = (output / "report.md").read_text(encoding="utf-8")
    assert results["package_licenses"][0]["licenses"] == ["MIT"]
    assert "Dependency license evidence" in report
