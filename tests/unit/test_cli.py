from codescan.cli import main


def test_version_prints_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "codescan 0.1.0"


def test_scan_help_is_available(capsys):
    assert main(["scan", "--help"]) == 0
    assert "PATH" in capsys.readouterr().out


def test_scan_rejects_missing_path(capsys, tmp_path):
    missing = tmp_path / "missing"
    assert main(["scan", str(missing)]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_scan_writes_report_csv_and_json(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('hello')\n", encoding="utf-8")
    output = tmp_path / "out"

    assert main(["scan", str(project), "--output", str(output)]) == 0
    assert {path.name for path in output.iterdir()} == {"report.md", "files.csv", "results.json"}
    assert "written" in capsys.readouterr().out
