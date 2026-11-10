from codescan.analyzers.repository import analyze_repository
from codescan.analyzers.tests_docs import analyze_tests_docs


def test_repository_analysis_reports_todo_and_large_file_without_content(tmp_path):
    source = tmp_path / "large.py"
    source.write_text("# TODO fix this\n" + "x = 1\n" * 3, encoding="utf-8")
    findings = analyze_repository(tmp_path, large_file_threshold=10)
    titles = {finding.title for finding in findings}
    assert "TODO/FIXME markers detected" in titles
    todo = next(item for item in findings if item.title == "TODO/FIXME markers detected")
    assert todo.evidence[0].path == "large.py"
    assert "TODO" in todo.summary
    assert "fix this" not in todo.summary


def test_repository_secret_filename_finding_never_contains_contents(tmp_path):
    secret = tmp_path / ".env"
    secret.write_text("API_TOKEN=secret-value", encoding="utf-8")
    findings = analyze_repository(tmp_path)
    assert any(item.title == "Potential secrets file detected" for item in findings)
    assert all("secret-value" not in item.summary for item in findings)


def test_tests_docs_discovery_distinguishes_tests_from_measured_coverage(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Project overview", encoding="utf-8")
    findings, status = analyze_tests_docs(tmp_path)
    assert status == "completed"
    assert {item.title for item in findings} >= {"Tests detected", "Project documentation detected"}
    assert not any("coverage percentage" in item.summary.lower() for item in findings)


def test_missing_tests_or_docs_are_unknown_signals_not_quality_verdicts(tmp_path):
    findings, _ = analyze_tests_docs(tmp_path)
    assert all("not detected" in item.summary for item in findings)
    assert all(item.severity is None for item in findings)
