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


def test_cobertura_coverage_percentage_is_parsed_with_evidence(tmp_path):
    (tmp_path / "coverage.xml").write_text(
        '<coverage line-rate="0.875" lines-covered="7" lines-valid="8"/>',
        encoding="utf-8",
    )

    findings, status = analyze_tests_docs(tmp_path)

    coverage = next(item for item in findings if item.id == "COVERAGE-ARTIFACT-001")
    assert status == "completed"
    assert "87.5%" in coverage.summary
    assert coverage.evidence[0].detail == "7/8 lines (87.5%)"


def test_lcov_coverage_percentage_is_parsed_from_line_totals(tmp_path):
    (tmp_path / "lcov.info").write_text("TN:\nSF:src/main.py\nLF:10\nLH:6\nend_of_record\n")

    findings, _ = analyze_tests_docs(tmp_path)

    coverage = next(item for item in findings if item.id == "COVERAGE-ARTIFACT-001")
    assert "60.0%" in coverage.summary
    assert coverage.evidence[0].detail == "6/10 lines (60.0%)"


def test_jacoco_coverage_percentage_is_parsed_from_line_counters(tmp_path):
    (tmp_path / "jacoco.xml").write_text(
        '<report><counter type="LINE" missed="3" covered="9"/></report>',
        encoding="utf-8",
    )

    findings, status = analyze_tests_docs(tmp_path)

    coverage = next(item for item in findings if item.id == "COVERAGE-ARTIFACT-001")
    assert status == "completed"
    assert "75.0%" in coverage.summary
    assert coverage.evidence[0].detail == "9/12 lines (75.0%)"


def test_invalid_coverage_artifact_is_partial_and_does_not_invent_a_percentage(tmp_path):
    (tmp_path / "coverage.xml").write_text("<coverage line-rate='high'>", encoding="utf-8")

    findings, status = analyze_tests_docs(tmp_path)

    coverage = next(item for item in findings if item.id == "COVERAGE-ARTIFACT-001")
    assert status == "partial"
    assert "percentages are unavailable" in coverage.summary
