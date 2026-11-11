from codescan.analyzers.license_files import analyze_license_files
from codescan.renderers.markdown import render_report


def test_license_file_detection_only_reports_presence_and_path(tmp_path):
    (tmp_path / "LICENSE.md").write_text("A license title\n", encoding="utf-8")
    findings = analyze_license_files(tmp_path)
    assert len(findings) == 1
    assert findings[0].title == "License files detected"
    assert findings[0].evidence[0].path == "LICENSE.md"
    assert "does not determine" in findings[0].limitations[0]


def test_absence_is_reported_as_unavailable_not_legal_risk(tmp_path):
    findings = analyze_license_files(tmp_path)
    assert findings[0].title == "License file not detected"
    assert findings[0].severity is None


def test_markdown_report_includes_project_license_file_signal(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    findings = analyze_license_files(tmp_path)

    report = render_report("sample", [], findings=findings)

    assert "## Project license files" in report
    assert "License files detected" in report
    assert "LICENSE" in report
    assert "does not interpret the terms" in report
