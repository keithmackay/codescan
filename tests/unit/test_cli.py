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
    import json

    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text(
        "def long_function():\n" + "    value = 1\n" * 55, encoding="utf-8"
    )
    output = tmp_path / "out"

    assert main(["scan", str(project), "--output", str(output)]) == 0
    assert {path.name for path in output.iterdir()} == {"report.md", "files.csv", "results.json"}
    payload = json.loads((output / "results.json").read_text(encoding="utf-8"))
    complexity = next(item for item in payload["analyzers"] if item["name"] == "complexity")
    assert complexity["status"] == "completed"
    assert any(item["id"] == "COMPLEXITY-HOTSPOT-001" for item in payload["findings"])
    assert "written" in capsys.readouterr().out


def test_scan_isolates_analyzer_failure_and_writes_remaining_artifacts(tmp_path, monkeypatch):
    import json

    from codescan.cli import main

    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('still scanned')\n", encoding="utf-8")
    monkeypatch.setattr(
        "codescan.scan.analyze_repository",
        lambda _root: (_ for _ in ()).throw(RuntimeError("sensitive detail must not leak")),
    )

    assert main(["scan", str(project), "--output", str(tmp_path / "out")]) == 0

    payload = json.loads((tmp_path / "out" / "results.json").read_text(encoding="utf-8"))
    status = next(item for item in payload["analyzers"] if item["name"] == "repository_hygiene")
    failure = next(
        item for item in payload["findings"] if item["id"] == "ANALYZER-FAILED-REPOSITORY_HYGIENE"
    )
    assert status["status"] == "failed"
    assert "RuntimeError" in status["message"]
    assert all("sensitive detail" not in str(item) for item in payload["findings"])
    assert len(payload["files"]) == 1
    assert failure["category"] == "analyzer_status"


def test_decrypt_identities_cli_prompts_and_emits_csv(tmp_path, capsys, monkeypatch):
    from codescan.identity_crypto import encrypt_identity_map

    encrypted_path = tmp_path / "developers.enc.json"
    encrypted_path.write_text(
        encrypt_identity_map({"DEV-123": {"name": "Ada", "email": "ada@example.invalid"}}, "seed"),
        encoding="utf-8",
    )

    class InteractiveInput:
        @staticmethod
        def isatty():
            return True

    monkeypatch.setattr("codescan.cli.sys.stdin", InteractiveInput())
    monkeypatch.setattr("codescan.cli.getpass.getpass", lambda _prompt: "seed")

    assert main(["decrypt-identities", str(encrypted_path)]) == 0
    output = capsys.readouterr().out
    assert "developer_id,name,email" in output
    assert "DEV-123,Ada,ada@example.invalid" in output


def test_encrypt_seed_refuses_noninteractive_stdin(tmp_path, capsys):
    project = tmp_path / "repo"
    project.mkdir()
    assert main(["scan", str(project), "--encrypt-developer-identities"]) == 2
    assert "interactive terminal" in capsys.readouterr().err


def test_online_vulnerability_mode_displays_transfer_notice(tmp_path, capsys, monkeypatch):
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setattr("codescan.cli.write_scan", lambda *_args, **_kwargs: None)

    assert main(["scan", str(project), "--vulnerability-scan", "online"]) == 0
    assert "sends package names, versions, and ecosystems" in capsys.readouterr().err


def test_license_scan_requires_online_mode(tmp_path, capsys, monkeypatch):
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setattr(
        "codescan.cli.write_scan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("scan should not run")),
    )
    assert main(["scan", str(project), "--license-scan"]) == 2
    assert "requires --vulnerability-scan online" in capsys.readouterr().err
