"""Local scan orchestration and artifact writing."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from codescan.analyzers.complexity import analyze_python_complexity
from codescan.analyzers.dependencies import (
    Dependency,
    discover_dependencies,
    is_supported_manifest,
)
from codescan.analyzers.developer_activity import analyze_developer_activity
from codescan.analyzers.git_history import analyze_git_history
from codescan.analyzers.inventory import FileInventory, inventory_file
from codescan.analyzers.license_files import analyze_license_files
from codescan.analyzers.osv_scanner import Mode, OsvScanResult, run_osv_scanner
from codescan.analyzers.process_artifacts import analyze_process_artifacts
from codescan.analyzers.repository import analyze_repository
from codescan.analyzers.tests_docs import analyze_tests_docs
from codescan.discovery import IGNORED_DIRECTORIES, discover_files
from codescan.identity_crypto import encrypt_identity_map
from codescan.models import AnalyzerState, AnalyzerStatus, Evidence, Finding, ScanScope
from codescan.renderers.csv import render_inventory_csv
from codescan.renderers.json import render_results
from codescan.renderers.markdown import render_report

OUTPUT_FILES = ("report.md", "files.csv", "results.json", "developer-identities.enc.json")
T = TypeVar("T")


def _run_isolated(
    name: str, analyzer: Callable[[], T], fallback: T
) -> tuple[T, AnalyzerStatus | None, Finding | None]:
    try:
        return analyzer(), None, None
    except Exception as exc:  # noqa: BLE001 - isolate unexpected analyzer failures by design
        message = f"Analyzer failed ({type(exc).__name__}); remaining analyzers continued."
        safe_name = "".join(character if character.isalnum() else "_" for character in name.upper())
        status = AnalyzerStatus(name=name, status="failed", message=message)
        finding = Finding(
            id=f"ANALYZER-FAILED-{safe_name}",
            category="analyzer_status",
            title=f"{name.replace('_', ' ').title()} analyzer failed",
            summary=message,
            evidence=[Evidence(kind="analyzer_error", detail=type(exc).__name__)],
            limitations=["Other analyzer results may still be available in this scan."],
        )
        return fallback, status, finding


def _stage_text(destination: Path, content: str, sensitive: bool = False) -> Path:
    mode = 0o600 if sensitive else 0o666
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    open_descriptor: int | None = descriptor
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            open_descriptor = None
            stream.write(content)
        return temporary
    except BaseException:
        if open_descriptor is not None:
            os.close(open_descriptor)
        temporary.unlink(missing_ok=True)
        raise


def _atomic_write_artifacts(artifacts: dict[Path, tuple[str, bool]]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for destination, (content, sensitive) in artifacts.items():
            staged.append((destination, _stage_text(destination, content, sensitive)))
        for destination, temporary in staged:
            os.replace(temporary, destination)
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


def collect_inventory(
    root: Path, excludes: tuple[str, ...] = (), include_hidden: bool = False
) -> tuple[list[FileInventory], list[str]]:
    files = discover_files(root, excludes=excludes, include_hidden=include_hidden)
    inventory: list[FileInventory] = []
    unreadable: list[str] = []
    resolved_root = root.resolve()
    for discovered in files:
        try:
            inventory.append(inventory_file(discovered.path, resolved_root))
        except OSError:
            unreadable.append(discovered.relative_path)
    return inventory, unreadable


def write_scan(
    root: Path,
    output: Path,
    excludes: tuple[str, ...] = (),
    include_hidden: bool = False,
    force: bool = False,
    identity_seed: str | None = None,
    vulnerability_mode: Mode | None = None,
    osv_scanner: str = "osv-scanner",
    include_package_licenses: bool = False,
) -> None:
    root = root.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUT_FILES if (output / name).exists()]
    if existing and not force:
        raise FileExistsError(
            f"output already contains CodeScan artifacts: {', '.join(existing)} (use --force)"
        )
    inventory_result, inventory_error, inventory_failure = _run_isolated(
        "inventory",
        lambda: collect_inventory(root, excludes=excludes, include_hidden=include_hidden),
        cast(tuple[list[FileInventory], list[str]], ([], [])),
    )
    items, unreadable_files = inventory_result
    inventory_findings: list[Finding] = []
    if unreadable_files:
        inventory_findings.append(
            Finding(
                id="INVENTORY-UNREADABLE-001",
                category="inventory",
                title="Some discovered files could not be inventoried",
                summary=f"{len(unreadable_files)} file(s) could not be read and are omitted from the inventory.",
                evidence=[
                    Evidence(kind="unreadable_file", path=path, detail="file bytes unavailable")
                    for path in unreadable_files
                ],
                limitations=["File totals and LOC exclude the unreadable paths listed above."],
            )
        )
    root_label = root.name or root.anchor
    repository_findings, repository_error, repository_failure = _run_isolated(
        "repository_hygiene", lambda: analyze_repository(root), cast(list[Finding], [])
    )
    complexity_result, complexity_error, complexity_failure = _run_isolated(
        "complexity",
        lambda: analyze_python_complexity(root),
        cast(tuple[list[Finding], AnalyzerState, str], ([], "failed", "Analyzer failed.")),
    )
    complexity_findings, complexity_status, complexity_message = complexity_result
    license_findings, license_error, license_failure = _run_isolated(
        "project_license_files", lambda: analyze_license_files(root), cast(list[Finding], [])
    )
    tests_docs_result, tests_docs_error, tests_docs_failure = _run_isolated(
        "tests_docs_discovery",
        lambda: analyze_tests_docs(root),
        cast(tuple[list[Finding], AnalyzerState], ([], "failed")),
    )
    tests_docs_findings, tests_docs_status = tests_docs_result
    git_result, git_error, git_failure = _run_isolated(
        "git_history",
        lambda: analyze_git_history(root),
        cast(tuple[list[Finding], AnalyzerState], ([], "partial")),
    )
    git_findings, git_status = git_result
    process_findings, process_error, process_failure = _run_isolated(
        "process_artifacts", lambda: analyze_process_artifacts(root), cast(list[Finding], [])
    )
    dependency_result, dependency_failure_status, dependency_failure = _run_isolated(
        "dependency_inventory",
        lambda: (
            cast(
                tuple[list[Dependency], list[str]],
                discover_dependencies(root, include_errors=True),
            ),
            sum(
                is_supported_manifest(entry.path)
                for entry in discover_files(root, include_hidden=True)
            ),
        ),
        cast(tuple[tuple[list[Dependency], list[str]], int], (([], []), 0)),
    )
    (dependencies, dependency_errors), manifest_count = dependency_result
    if dependency_errors:
        process_findings.append(
            Finding(
                id="DEPENDENCY-PARSE-001",
                category="dependencies",
                title="Some dependency manifests could not be parsed",
                summary=f"{len(dependency_errors)} supported manifest(s) could not be parsed; review the analyzer status.",
                evidence=[
                    Evidence(kind="manifest_parse_error", detail=error.split(":", 1)[0])
                    for error in dependency_errors
                ],
                limitations=[
                    "No package manager was run; only static manifest parsing is performed."
                ],
            )
        )
    developer_findings: list[Finding] = []
    identity_map: dict[str, dict[str, str | int]] = {}
    if identity_seed is not None:
        developer_result, developer_error, developer_failure = _run_isolated(
            "developer_activity",
            lambda: analyze_developer_activity(root, identity_seed),
            cast(
                tuple[list[Finding], dict[str, dict[str, str | int]], AnalyzerState],
                ([], {}, "partial"),
            ),
        )
        developer_findings, identity_map, developer_status = developer_result
    else:
        developer_status = "skipped"
        developer_error = developer_failure = None
    vulnerability_run = (
        _run_isolated(
            "vulnerability_lookup",
            lambda: run_osv_scanner(
                root,
                executable=osv_scanner,
                mode=vulnerability_mode,
                include_licenses=include_package_licenses,
            ),
            OsvScanResult("partial", vulnerability_mode, message="OSV analyzer failed."),
        )
        if vulnerability_mode is not None
        else (
            OsvScanResult("skipped", "offline", message="Vulnerability scanning was not enabled."),
            None,
            None,
        )
    )
    vulnerability_result, vulnerability_error, vulnerability_failure = vulnerability_run
    analyzer_failures = [
        failure
        for failure in (
            inventory_failure,
            repository_failure,
            complexity_failure,
            license_failure,
            tests_docs_failure,
            git_failure,
            process_failure,
            developer_failure,
            dependency_failure,
            vulnerability_failure,
        )
        if failure is not None
    ]
    findings = [
        *analyzer_failures,
        *inventory_findings,
        *repository_findings,
        *complexity_findings,
        *license_findings,
        *tests_docs_findings,
        *git_findings,
        *process_findings,
        *developer_findings,
    ]
    if vulnerability_mode is None:
        vulnerability_message = "Vulnerability scanning was not enabled."
    elif vulnerability_result.message:
        vulnerability_message = vulnerability_result.message
    else:
        freshness_detail = (
            "cached database age is not exposed by OSV-Scanner."
            if vulnerability_result.mode == "offline"
            else "advisory modified timestamps are included when supplied."
        )
        vulnerability_message = (
            f"OSV-Scanner {vulnerability_result.scanner_version or 'unknown'}; "
            f"mode={vulnerability_result.mode}; "
            f"{len(vulnerability_result.vulnerabilities)} vulnerability finding(s); "
            f"{freshness_detail}"
        )
    analyzers = [
        inventory_error
        or AnalyzerStatus(name="inventory", status="partial" if unreadable_files else "completed"),
        repository_error or AnalyzerStatus(name="repository_hygiene", status="completed"),
        license_error or AnalyzerStatus(name="project_license_files", status="completed"),
        tests_docs_error or AnalyzerStatus(name="tests_docs_discovery", status=tests_docs_status),
        git_error or AnalyzerStatus(name="git_history", status=git_status),
        process_error or AnalyzerStatus(name="process_artifacts", status="completed"),
        (
            AnalyzerStatus(
                name="developer_activity",
                status=developer_status,
                message=(
                    None
                    if identity_seed is not None
                    else "Requires --encrypt-developer-identities."
                ),
            )
            if developer_error is None
            else developer_error
        ),
        complexity_error
        or AnalyzerStatus(
            name="complexity",
            status=complexity_status,
            message=complexity_message,
        ),
        dependency_failure_status
        or AnalyzerStatus(
            name="dependency_inventory",
            status=(
                "partial" if dependency_errors else ("completed" if manifest_count else "skipped")
            ),
            message=(
                f"{len(dependency_errors)} manifest parse error(s)."
                if dependency_errors
                else (None if manifest_count else "No supported dependency manifest detected.")
            ),
        ),
        vulnerability_error
        or AnalyzerStatus(
            name="vulnerability_lookup",
            status=vulnerability_result.status,
            message=vulnerability_message,
        ),
        AnalyzerStatus(
            name="package_license_lookup",
            status=vulnerability_result.status if include_package_licenses else "skipped",
            message=(
                vulnerability_result.message
                or f"{len(vulnerability_result.licenses)} record(s) from deps.dev via OSV-Scanner."
                if include_package_licenses
                else "Requires --license-scan with online vulnerability mode."
            ),
        ),
    ]
    scan_scope = ScanScope(
        include_hidden=include_hidden,
        exclude_patterns=excludes,
        default_ignored_directories=tuple(sorted(IGNORED_DIRECTORIES)),
        follow_symlinks=False,
    )
    artifacts: dict[Path, tuple[str, bool]] = {
        output / "report.md": (
            render_report(
                root_label,
                items,
                findings=findings,
                dependencies=dependencies,
                vulnerabilities=vulnerability_result.vulnerabilities,
                analyzers=analyzers,
                package_licenses=vulnerability_result.licenses,
                scope=scan_scope,
            ),
            False,
        ),
        output / "files.csv": (render_inventory_csv(items), False),
        output / "results.json": (
            render_results(
                root_label,
                items,
                str(uuid.uuid4()),
                findings=findings,
                analyzers=analyzers,
                dependencies=dependencies,
                vulnerabilities=vulnerability_result.vulnerabilities,
                package_licenses=vulnerability_result.licenses,
                scope=scan_scope,
            ),
            False,
        ),
    }
    identity_path = output / "developer-identities.enc.json"
    if identity_seed is not None and identity_map:
        artifacts[identity_path] = (
            encrypt_identity_map(identity_map, identity_seed),
            True,
        )
    _atomic_write_artifacts(artifacts)
    if (identity_seed is None or not identity_map) and force and identity_path.exists():
        identity_path.unlink()
