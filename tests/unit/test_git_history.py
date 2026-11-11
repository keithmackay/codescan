import subprocess
from pathlib import Path

from codescan.analyzers.git_history import analyze_git_history
from codescan.analyzers.process_artifacts import analyze_process_artifacts


def make_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test Dev"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.invalid"], check=True
    )


def commit(path: Path, filename: str, content: str) -> None:
    (path / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", f"update {filename}"], check=True)


def test_history_reports_concentration_without_names_or_emails(tmp_path):
    make_repo(tmp_path)
    commit(tmp_path, "one.py", "x = 1\n")
    commit(tmp_path, "two.py", "x = 2\n")
    findings, status = analyze_git_history(tmp_path)
    assert status == "completed"
    concentration = next(item for item in findings if item.category == "contributor_concentration")
    assert "100%" in concentration.summary
    assert "Test Dev" not in concentration.summary
    assert "test@example.invalid" not in str(concentration)


def test_history_unavailable_is_partial_not_a_negative_finding(tmp_path):
    findings, status = analyze_git_history(tmp_path)
    assert status == "skipped"
    assert findings == []


def test_process_artifact_detection_is_descriptive(tmp_path):
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "CODEOWNERS").write_text("* @team\n", encoding="utf-8")
    findings = analyze_process_artifacts(tmp_path)
    assert {item.title for item in findings} == {"Process configuration artifacts detected"}
    finding = findings[0]
    assert "CI/CD" in finding.summary
    assert "followed" in finding.limitations[0]
