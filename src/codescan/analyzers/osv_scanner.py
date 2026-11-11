"""Optional OSV-Scanner subprocess adapter and JSON result normalizer."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Mode = Literal["offline", "online"]
ScanStatus = Literal["completed", "partial", "skipped"]


@dataclass(frozen=True)
class Vulnerability:
    advisory_id: str
    aliases: list[str]
    package: str
    ecosystem: str
    version: str
    fixed_versions: list[str]
    source_path: str | None
    summary: str | None
    severity: str | None
    modified: str | None = None
    source: str = "OSV.dev via OSV-Scanner"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OsvScanResult:
    status: ScanStatus
    mode: Mode
    scanner_version: str | None = None
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    message: str | None = None
    licenses: list[PackageLicense] = field(default_factory=list)


@dataclass(frozen=True)
class PackageLicense:
    package: str
    ecosystem: str
    version: str
    licenses: list[str]
    violations: list[str]
    source_path: str | None
    source: str = "deps.dev via OSV-Scanner"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _relative_source(source_path: Any, root: Path) -> str | None:
    if not isinstance(source_path, str) or not source_path:
        return None
    path = Path(source_path)
    try:
        if path.is_absolute():
            return path.resolve().relative_to(root.resolve()).as_posix()
        return (root / path).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        # Do not leak an absolute path outside the scan root into the report.
        return path.name


def _fixed_versions(vulnerability: dict[str, Any]) -> list[str]:
    fixed: set[str] = set()
    for affected in vulnerability.get("affected", []):
        if not isinstance(affected, dict):
            continue
        for version_range in affected.get("ranges", []):
            if not isinstance(version_range, dict):
                continue
            for event in version_range.get("events", []):
                if isinstance(event, dict) and isinstance(event.get("fixed"), str):
                    fixed.add(event["fixed"])
    return sorted(fixed)


def normalize_osv_results(payload: dict[str, Any], root: Path) -> list[Vulnerability]:
    """Extract stable, report-ready vulnerability records from OSV-Scanner JSON."""
    normalized: dict[tuple[str, str, str, str], Vulnerability] = {}
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        source_info = result.get("source") or {}
        source_path = _relative_source(source_info.get("path"), root)
        for package_group in result.get("packages", []):
            if not isinstance(package_group, dict):
                continue
            package = package_group.get("package") or {}
            name = package.get("name")
            ecosystem = package.get("ecosystem")
            version = package.get("version")
            if not (
                isinstance(name, str) and isinstance(ecosystem, str) and isinstance(version, str)
            ):
                continue
            for vulnerability in package_group.get("vulnerabilities", []):
                if not isinstance(vulnerability, dict) or not isinstance(
                    vulnerability.get("id"), str
                ):
                    continue
                advisory_id = vulnerability["id"]
                aliases = sorted(
                    alias for alias in vulnerability.get("aliases", []) if isinstance(alias, str)
                )
                specific = vulnerability.get("database_specific") or {}
                severity_value = specific.get("severity") if isinstance(specific, dict) else None
                if not isinstance(severity_value, str):
                    severity_entries = vulnerability.get("severity", [])
                    if isinstance(severity_entries, list):
                        for entry in severity_entries:
                            if isinstance(entry, dict) and isinstance(entry.get("score"), str):
                                severity_type = entry.get("type")
                                severity_value = (
                                    f"{severity_type}: {entry['score']}"
                                    if isinstance(severity_type, str)
                                    else entry["score"]
                                )
                                break
                record = Vulnerability(
                    advisory_id=advisory_id,
                    aliases=aliases,
                    package=name,
                    ecosystem=ecosystem,
                    version=version,
                    fixed_versions=_fixed_versions(vulnerability),
                    source_path=source_path,
                    summary=vulnerability.get("summary")
                    if isinstance(vulnerability.get("summary"), str)
                    else None,
                    severity=severity_value if isinstance(severity_value, str) else None,
                    modified=(
                        vulnerability.get("modified")
                        if isinstance(vulnerability.get("modified"), str)
                        else None
                    ),
                )
                normalized[(ecosystem, name, version, advisory_id)] = record
    return sorted(
        normalized.values(),
        key=lambda item: (
            item.ecosystem.casefold(),
            item.package.casefold(),
            item.version,
            item.advisory_id,
        ),
    )


def normalize_osv_licenses(payload: dict[str, Any], root: Path) -> list[PackageLicense]:
    """Extract package license metadata returned by OSV-Scanner's optional license feature."""
    normalized: dict[tuple[str, str, str], PackageLicense] = {}

    def license_values(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        values = {
            item if isinstance(item, str) else item.get("license") or item.get("id")
            for item in value
            if isinstance(item, str)
            or (isinstance(item, dict) and isinstance(item.get("license") or item.get("id"), str))
        }
        return sorted(item for item in values if isinstance(item, str))

    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        source_info = result.get("source") or {}
        source_path = _relative_source(source_info.get("path"), root)
        for package_group in result.get("packages", []):
            if not isinstance(package_group, dict):
                continue
            package = package_group.get("package") or {}
            name, ecosystem, version = (
                package.get("name"),
                package.get("ecosystem"),
                package.get("version"),
            )
            if not (
                isinstance(name, str) and isinstance(ecosystem, str) and isinstance(version, str)
            ):
                continue
            licenses = license_values(package_group.get("licenses"))
            violations = license_values(package_group.get("license_violations"))
            if not licenses and not violations:
                continue
            normalized[(ecosystem, name, version)] = PackageLicense(
                package=name,
                ecosystem=ecosystem,
                version=version,
                licenses=licenses,
                violations=violations,
                source_path=source_path,
            )
    return sorted(
        normalized.values(),
        key=lambda item: (item.ecosystem.casefold(), item.package.casefold(), item.version),
    )


def run_osv_scanner(
    root: Path,
    executable: str = "osv-scanner",
    mode: Mode = "offline",
    timeout_seconds: int = 120,
    include_licenses: bool = False,
) -> OsvScanResult:
    """Run OSV-Scanner without remediation, returning sanitized result state."""
    if mode not in {"offline", "online"}:
        raise ValueError("OSV scan mode must be offline or online")
    if include_licenses and mode != "online":
        raise ValueError("license scanning currently requires explicit online mode")
    try:
        version_result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        version_text = (version_result.stdout or version_result.stderr).strip()
        match = re.search(r"\d+\.\d+\.\d+(?:[-+][\w.-]+)?", version_text)
        scanner_version = match.group(0) if match else (version_text[:128] or None)
    except FileNotFoundError:
        return OsvScanResult("skipped", mode, message="OSV-Scanner is not installed or not found.")
    except (OSError, subprocess.TimeoutExpired):
        return OsvScanResult("partial", mode, message="Could not determine OSV-Scanner version.")

    command = [executable]
    if mode == "offline":
        command.append("--offline")
    if include_licenses:
        command.append("--licenses")
    command.extend(["scan", "source", "-r", str(root.resolve()), "--format", "json"])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return OsvScanResult(
            "skipped", mode, scanner_version, message="OSV-Scanner executable disappeared."
        )
    except subprocess.TimeoutExpired:
        return OsvScanResult("partial", mode, scanner_version, message="OSV-Scanner timed out.")
    except OSError:
        return OsvScanResult(
            "partial", mode, scanner_version, message="OSV-Scanner could not be started."
        )

    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise TypeError("expected JSON object")
        vulnerabilities = normalize_osv_results(payload, root)
        licenses = normalize_osv_licenses(payload, root) if include_licenses else []
    except (json.JSONDecodeError, ValueError, TypeError):
        return OsvScanResult(
            "partial",
            mode,
            scanner_version,
            message=f"OSV-Scanner returned unusable output (exit {result.returncode}).",
        )
    if result.returncode not in {0, 1}:
        return OsvScanResult(
            "partial",
            mode,
            scanner_version,
            vulnerabilities,
            f"OSV-Scanner returned exit {result.returncode}; results may be incomplete.",
            licenses,
        )
    return OsvScanResult("completed", mode, scanner_version, vulnerabilities, licenses=licenses)
