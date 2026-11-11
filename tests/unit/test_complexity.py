from codescan.analyzers.complexity import analyze_python_complexity


def test_python_ast_complexity_reports_evidence_for_complex_function(tmp_path):
    source = tmp_path / "module.py"
    source.write_text(
        "def decide(a, b, c):\n"
        "    if a and b:\n"
        "        for item in c:\n"
        "            if item:\n"
        "                return item\n" + "    value = 0\n" * 50 + "    return None\n",
        encoding="utf-8",
    )

    findings, status, message = analyze_python_complexity(tmp_path)

    finding = next(item for item in findings if item.id == "COMPLEXITY-HOTSPOT-001")
    assert status == "completed"
    assert "1 Python function" in message
    assert finding.evidence[0].path == "module.py"
    assert "decide" in finding.evidence[0].detail
    assert "cyclomatic=5" in finding.evidence[0].detail
    assert "nesting=3" in finding.evidence[0].detail
    assert "lines=56" in finding.evidence[0].detail


def test_python_complexity_ignores_branch_words_in_strings_and_comments(tmp_path):
    (tmp_path / "simple.py").write_text(
        'def simple():\n    text = "if else while"\n    # if while for\n    return text\n',
        encoding="utf-8",
    )

    findings, status, message = analyze_python_complexity(tmp_path)

    assert findings == []
    assert status == "completed"
    assert "cyclomatic complexity above 10" not in message


def test_python_complexity_partial_when_source_cannot_parse(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    findings, status, message = analyze_python_complexity(tmp_path)

    assert status == "partial"
    assert "could not be parsed" in message
    assert any(item.id == "COMPLEXITY-PARSE-001" for item in findings)


def test_python_complexity_skips_when_no_python_source_exists(tmp_path):
    findings, status, message = analyze_python_complexity(tmp_path)

    assert findings == []
    assert status == "skipped"
    assert "No Python source" in message
