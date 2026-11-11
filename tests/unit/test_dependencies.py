import json

from codescan.analyzers.dependencies import discover_dependencies


def test_reads_pinned_requirements_and_ignores_comments(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "requests==2.32.1\n# skip==1.0\nflask>=3.0\n", encoding="utf-8"
    )
    dependencies = discover_dependencies(tmp_path)
    assert {(item.name, item.version, item.version_kind) for item in dependencies} == {
        ("requests", "==2.32.1", "declared"),
        ("flask", ">=3.0", "declared"),
    }
    assert dependencies[0].ecosystem == "pypi"


def test_reads_package_lock_resolved_versions(tmp_path):
    content = {
        "name": "sample",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "sample"},
            "node_modules/left-pad": {"version": "1.3.0"},
            "node_modules/@scope/lib": {"version": "2.1.0"},
        },
    }
    (tmp_path / "package-lock.json").write_text(json.dumps(content), encoding="utf-8")
    dependencies = discover_dependencies(tmp_path)
    assert {(item.name, item.version) for item in dependencies} == {
        ("left-pad", "1.3.0"),
        ("@scope/lib", "2.1.0"),
    }


def test_reads_go_mod_requirements(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module example.com/app\n\ngo 1.23\nrequire (\n example.com/lib v1.2.3\n example.com/other v0.9.0 // indirect\n)\n",
        encoding="utf-8",
    )
    dependencies = discover_dependencies(tmp_path)
    assert {(item.name, item.version) for item in dependencies} == {
        ("example.com/lib", "v1.2.3"),
        ("example.com/other", "v0.9.0"),
    }


def test_malformed_manifest_is_reported_without_aborting_other_manifests(tmp_path):
    (tmp_path / "package-lock.json").write_text("not-json", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("idna==3.7\n", encoding="utf-8")
    dependencies, errors = discover_dependencies(tmp_path, include_errors=True)
    assert [item.name for item in dependencies] == ["idna"]
    assert len(errors) == 1
    assert "package-lock.json" in errors[0]


def test_dependency_paths_are_relative_and_no_package_manager_is_run(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("urllib3==2.2.1\n", encoding="utf-8")
    dependency = discover_dependencies(tmp_path)[0]
    assert dependency.source_path == "requirements.txt"
    assert str(tmp_path) not in dependency.source_path


def test_dependency_inventory_is_written_to_json_and_markdown(tmp_path):
    from codescan.scan import write_scan

    (tmp_path / "requirements.txt").write_text("requests==2.32.1\n", encoding="utf-8")
    output = tmp_path / "report-output"
    write_scan(tmp_path, output)
    results = json.loads((output / "results.json").read_text(encoding="utf-8"))
    report = (output / "report.md").read_text(encoding="utf-8")
    assert results["dependencies"][0]["name"] == "requests"
    assert "Dependency inventory" in report
    assert "No vulnerability results are available" in report
    status = next(item for item in results["analyzers"] if item["name"] == "vulnerability_lookup")
    assert status["status"] == "skipped"
    assert "disabled" in report.lower()


def test_reads_legacy_npm_package_lock_nested_dependencies(tmp_path):
    content = {
        "name": "root",
        "lockfileVersion": 1,
        "dependencies": {
            "left-pad": {"version": "1.3.0", "dependencies": {"nested": {"version": "2.0.0"}}}
        },
    }
    (tmp_path / "package-lock.json").write_text(json.dumps(content), encoding="utf-8")
    dependencies = discover_dependencies(tmp_path)
    assert {(item.name, item.version) for item in dependencies} == {
        ("left-pad", "1.3.0"),
        ("nested", "2.0.0"),
    }


def test_reads_pyproject_optional_dependencies(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests>=2.30"]\n'
        '[project.optional-dependencies]\ntest = ["pytest==8.0"]\n',
        encoding="utf-8",
    )
    dependencies = discover_dependencies(tmp_path)
    assert {(item.name, item.version) for item in dependencies} == {
        ("requests", ">=2.30"),
        ("pytest", "==8.0"),
    }


def test_reads_nuget_packages_lock_resolved_versions(tmp_path):
    content = {
        "version": 1,
        "dependencies": {
            "net8.0": {
                "Newtonsoft.Json": {"type": "Direct", "requested": "13.0.1", "resolved": "13.0.1"}
            }
        },
    }
    (tmp_path / "packages.lock.json").write_text(json.dumps(content), encoding="utf-8")
    dependencies = discover_dependencies(tmp_path)
    assert [(item.name, item.version, item.ecosystem) for item in dependencies] == [
        ("Newtonsoft.Json", "13.0.1", "nuget")
    ]


def test_reads_maven_and_nuget_project_declarations(tmp_path):
    (tmp_path / "pom.xml").write_text(
        "<project xmlns='http://maven.apache.org/POM/4.0.0'><dependencies>"
        "<dependency><groupId>org.example</groupId><artifactId>sample</artifactId><version>1.2</version></dependency>"
        "</dependencies></project>",
        encoding="utf-8",
    )
    (tmp_path / "App.csproj").write_text(
        "<Project><ItemGroup><PackageReference Include='Example.Package' Version='2.4.0' /></ItemGroup></Project>",
        encoding="utf-8",
    )
    dependencies = discover_dependencies(tmp_path)
    assert {(item.ecosystem, item.name, item.version) for item in dependencies} == {
        ("maven", "org.example:sample", "1.2"),
        ("nuget", "Example.Package", "2.4.0"),
    }


def test_reads_composer_lock_and_gemfile_lock(tmp_path):
    (tmp_path / "composer.lock").write_text(
        json.dumps({"packages": [{"name": "vendor/library", "version": "1.2.3"}]}),
        encoding="utf-8",
    )
    (tmp_path / "Gemfile.lock").write_text(
        "GEM\n  remote: https://rubygems.org/\n  specs:\n"
        "    rack (3.0.8)\n    rake (13.2.1)\n\nDEPENDENCIES\n  rack\n",
        encoding="utf-8",
    )
    dependencies = discover_dependencies(tmp_path)
    assert {(item.ecosystem, item.name, item.version) for item in dependencies} == {
        ("composer", "vendor/library", "1.2.3"),
        ("rubygems", "rack", "3.0.8"),
        ("rubygems", "rake", "13.2.1"),
    }


def test_reads_poetry_lock_package_records(tmp_path):
    (tmp_path / "poetry.lock").write_text(
        '[[package]]\nname = "requests"\nversion = "2.32.1"\n', encoding="utf-8"
    )
    dependencies = discover_dependencies(tmp_path)
    assert [(item.name, item.version) for item in dependencies] == [("requests", "2.32.1")]
