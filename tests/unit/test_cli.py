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
