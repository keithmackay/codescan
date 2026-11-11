"""AST-based complexity signals for Python source files."""

from __future__ import annotations

import ast
from pathlib import Path

from codescan.discovery import discover_files
from codescan.models import AnalyzerState, Evidence, Finding

MAX_SOURCE_BYTES = 10 * 1024 * 1024
COMPLEXITY_LIMIT = 10
FUNCTION_LOC_LIMIT = 50
NESTING_LIMIT = 4


class _FunctionMetrics(ast.NodeVisitor):
    def __init__(self) -> None:
        self.cyclomatic = 1
        self.max_nesting = 0
        self._nesting = 0

    def visit_If(self, node: ast.If) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_For(self, node: ast.For) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_While(self, node: ast.While) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.cyclomatic += 1
        self._visit_control(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.cyclomatic += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        cases = [
            case
            for case in node.cases
            if not (isinstance(case.pattern, ast.MatchAs) and case.pattern.name is None)
        ]
        self.cyclomatic += len(cases)
        self._visit_control(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Nested functions are measured independently, not as part of their parent.
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def _visit_control(self, node: ast.AST) -> None:
        self._nesting += 1
        self.max_nesting = max(self.max_nesting, self._nesting)
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        self._nesting -= 1


def _function_nodes(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def analyze_python_complexity(
    root: Path,
) -> tuple[list[Finding], AnalyzerState, str]:
    source_files = [
        entry
        for entry in discover_files(root, include_hidden=True)
        if entry.path.suffix.lower() == ".py"
    ]
    if not source_files:
        return (
            [],
            "skipped",
            "No Python source files detected; other languages are not measured yet.",
        )

    functions_analyzed = 0
    parse_errors: list[str] = []
    hotspots: list[Evidence] = []
    for entry in source_files:
        try:
            if entry.path.stat().st_size > MAX_SOURCE_BYTES:
                parse_errors.append(entry.relative_path)
                continue
            source = entry.path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=entry.relative_path)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError, RecursionError):
            parse_errors.append(entry.relative_path)
            continue

        for function in _function_nodes(tree):
            functions_analyzed += 1
            metrics = _FunctionMetrics()
            for statement in function.body:
                metrics.visit(statement)
            end_line = function.end_lineno or function.lineno
            function_loc = end_line - function.lineno + 1
            reasons = []
            if metrics.cyclomatic > COMPLEXITY_LIMIT:
                reasons.append(f"cyclomatic={metrics.cyclomatic} (> {COMPLEXITY_LIMIT})")
            if function_loc > FUNCTION_LOC_LIMIT:
                reasons.append(f"lines={function_loc} (> {FUNCTION_LOC_LIMIT})")
            if metrics.max_nesting > NESTING_LIMIT:
                reasons.append(f"nesting={metrics.max_nesting} (> {NESTING_LIMIT})")
            if reasons:
                name = function.name
                hotspots.append(
                    Evidence(
                        kind="python_function_metrics",
                        path=entry.relative_path,
                        detail=(
                            f"{name} at line {function.lineno}: "
                            f"cyclomatic={metrics.cyclomatic}, lines={function_loc}, "
                            f"nesting={metrics.max_nesting}; " + ", ".join(reasons)
                        ),
                    )
                )
    findings: list[Finding] = []
    if hotspots:
        findings.append(
            Finding(
                id="COMPLEXITY-HOTSPOT-001",
                category="code_quality",
                title="Python function complexity signals detected",
                summary=(
                    f"{len(hotspots)} function(s) exceeded one or more documented thresholds "
                    "for cyclomatic complexity, physical function length, or nested control flow."
                ),
                evidence=hotspots,
                limitations=[
                    "AST metrics cover Python only; thresholds are review prompts, not quality scores. Function length includes its definition line and blank/comment lines.",
                    "Cyclomatic complexity counts conditional branches, loops, exception handlers, match cases, conditional expressions, and boolean operators using Python's AST.",
                ],
            )
        )
    if parse_errors:
        findings.append(
            Finding(
                id="COMPLEXITY-PARSE-001",
                category="code_quality",
                title="Some Python files could not be analyzed for complexity",
                summary=f"{len(parse_errors)} Python source file(s) were skipped because they were unreadable, oversized, or invalid syntax.",
                evidence=[
                    Evidence(kind="unparsed_source_file", path=path) for path in parse_errors
                ],
                limitations=["Metrics may not cover all Python source files."],
            )
        )
    status: AnalyzerState = "partial" if parse_errors else "completed"
    message = (
        f"Analyzed {functions_analyzed} Python function(s); {len(hotspots)} exceeded a threshold."
    )
    if parse_errors:
        message += f" {len(parse_errors)} Python file(s) could not be parsed."
    return findings, status, message
