import json

import pytest

from codescan.identity_crypto import decrypt_identity_map, developer_id, encrypt_identity_map


def test_encrypt_decrypt_round_trip_and_wrong_seed_rejected():
    identities = {"DEV-123": {"name": "Ada Example", "email": "ada@example.invalid"}}
    encrypted = encrypt_identity_map(identities, "correct horse battery staple")
    assert "ada@example.invalid" not in encrypted
    assert decrypt_identity_map(encrypted, "correct horse battery staple") == identities
    with pytest.raises(ValueError, match="decrypt"):
        decrypt_identity_map(encrypted, "wrong seed")


def test_envelope_is_versioned_and_randomized():
    data = {"DEV-1": {"name": "Grace", "email": "grace@example.invalid"}}
    first = encrypt_identity_map(data, "seed")
    second = encrypt_identity_map(data, "seed")
    assert json.loads(first)["format_version"] == 1
    assert first != second


def test_developer_ids_are_stable_unique_and_do_not_reveal_identity():
    seed = "a user supplied seed"
    first = developer_id("Ada Lovelace", "ada@example.invalid", seed)
    assert first == developer_id("Ada Lovelace", "ada@example.invalid", seed)
    assert first != developer_id("Grace Hopper", "grace@example.invalid", seed)
    assert "ada" not in first.lower()


def test_scan_writes_pseudonymous_activity_and_encrypted_map(tmp_path):
    import subprocess

    from codescan.scan import write_scan

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Secret Name"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "private@example.invalid"], check=True
    )
    (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "main.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
    output = tmp_path / "out"

    write_scan(repo, output, identity_seed="seed phrase")

    report = (output / "report.md").read_text(encoding="utf-8")
    encrypted = (output / "developer-identities.enc.json").read_text(encoding="utf-8")
    assert "DEV-" in report
    assert "Secret Name" not in report
    assert "private@example.invalid" not in report
    assert "private@example.invalid" not in encrypted
    mapping = decrypt_identity_map(encrypted, "seed phrase")
    assert next(iter(mapping.values()))["email"] == "private@example.invalid"
