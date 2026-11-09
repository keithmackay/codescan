from codescan.analyzers.inventory import inventory_file
from codescan.discovery import detect_language, discover_files


def test_language_mapping_covers_initial_languages():
    cases = {
        "app.cs": "C#",
        "Main.java": "Java",
        "app.js": "JavaScript",
        "app.ts": "TypeScript",
        "app.cpp": "C/C++",
        "main.go": "Go",
        "main.py": "Python",
        "index.php": "PHP",
        "task.rb": "Ruby",
        "schema.sql": "SQL",
        "unknown.zzz": "unknown",
    }
    for filename, expected in cases.items():
        assert detect_language(filename) == expected


def test_inventory_counts_nonblank_physical_lines(tmp_path):
    source = tmp_path / "sample.py"
    source.write_bytes(b"one\r\n\r\ntwo")
    item = inventory_file(source, tmp_path)
    assert item.language == "Python"
    assert item.loc == 2
    assert item.blank_lines == 1
    assert item.total_lines == 3
    assert item.bytes == 10


def test_discovery_skips_common_generated_folders_and_git(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "internal.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "vendor.js").write_text("x\n", encoding="utf-8")
    assert [item.relative_path for item in discover_files(tmp_path)] == ["src/main.py"]
