"""Offline parsing of common dependency manifests and lockfiles."""

from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from codescan.discovery import discover_files

MAX_MANIFEST_BYTES = 20 * 1024 * 1024
PYTHON_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*((?:===|==|~=|!=|<=|>=|<|>).+?)\s*$"
)
GO_REQUIRE = re.compile(r"^\s*([^\s]+)\s+(v[^\s]+)")
GEM_SPEC = re.compile(r"^    ([A-Za-z0-9_.-]+) \(([^)]+)\)$")


@dataclass(frozen=True, order=True)
class Dependency:
    ecosystem: str
    name: str
    version: str
    source_path: str
    version_kind: str = "resolved"
    source_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _requirements(path: Path, relative: str) -> list[Dependency]:
    found: list[Dependency] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        candidate = line.split(";", 1)[0].strip()
        match = PYTHON_REQUIREMENT.match(candidate)
        if match and not line.lstrip().startswith("#"):
            found.append(Dependency("pypi", match.group(1), match.group(2), relative, "declared"))
    return found


def _json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("expected a JSON object")
    return data


def _package_lock(path: Path, relative: str) -> list[Dependency]:
    data = _json_object(path)
    packages = data.get("packages", {})
    found = []
    for lock_path, entry in packages.items() if isinstance(packages, dict) else []:
        if (
            not lock_path
            or not isinstance(entry, dict)
            or not isinstance(entry.get("version"), str)
        ):
            continue
        marker = "node_modules/"
        if marker not in lock_path:
            continue
        name = lock_path.rsplit(marker, 1)[-1]
        if name:
            found.append(Dependency("npm", name, entry["version"], relative))
    if not found:
        pending = [data.get("dependencies")]
        while pending:
            dependencies = pending.pop()
            if not isinstance(dependencies, dict):
                continue
            for name, entry in dependencies.items():
                if not isinstance(entry, dict):
                    continue
                version = entry.get("version")
                if isinstance(name, str) and isinstance(version, str):
                    found.append(Dependency("npm", name, version, relative))
                pending.append(entry.get("dependencies"))
    return found


def _go_mod(path: Path, relative: str) -> list[Dependency]:
    found = []
    in_block = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.split("//", 1)[0].strip()
        if stripped.replace(" ", "") == "require(":
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        candidate = stripped
        candidate = candidate.removeprefix("require ")
        match = (
            GO_REQUIRE.match(candidate)
            if (in_block or line.strip().startswith("require "))
            else None
        )
        if match:
            found.append(Dependency("go", match.group(1), match.group(2), relative))
    return found


def _toml(path: Path, relative: str) -> list[Dependency]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    found: list[Dependency] = []
    project = data.get("project", {})
    if isinstance(project, dict):
        requirements = project.get("dependencies", [])
        if isinstance(requirements, list):
            for requirement in requirements:
                if not isinstance(requirement, str):
                    continue
                match = PYTHON_REQUIREMENT.match(requirement)
                if match:
                    found.append(
                        Dependency("pypi", match.group(1), match.group(2), relative, "declared")
                    )
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for requirements in optional.values():
            if not isinstance(requirements, list):
                continue
            for requirement in requirements:
                if isinstance(requirement, str):
                    match = PYTHON_REQUIREMENT.match(requirement)
                    if match:
                        found.append(
                            Dependency("pypi", match.group(1), match.group(2), relative, "declared")
                        )
    packages = data.get("package", [])
    if isinstance(packages, list):
        for package in packages:
            if not isinstance(package, dict):
                continue
            name, version = package.get("name"), package.get("version")
            if isinstance(name, str) and isinstance(version, str):
                found.append(Dependency("pypi", name, version, relative))
    return found


def _composer_lock(path: Path, relative: str) -> list[Dependency]:
    data = _json_object(path)
    found = []
    for section in ("packages", "packages-dev"):
        packages = data.get(section, [])
        if not isinstance(packages, list):
            continue
        for package in packages:
            if not isinstance(package, dict):
                continue
            name, version = package.get("name"), package.get("version")
            if isinstance(name, str) and isinstance(version, str):
                found.append(Dependency("composer", name, version, relative))
    return found


def _nuget_packages_lock(path: Path, relative: str) -> list[Dependency]:
    data = _json_object(path)
    found: list[Dependency] = []
    frameworks = data.get("dependencies", {})
    if not isinstance(frameworks, dict):
        return found
    for packages in frameworks.values():
        if not isinstance(packages, dict):
            continue
        for name, details in packages.items():
            if not isinstance(details, dict):
                continue
            version = details.get("resolved")
            if isinstance(name, str) and isinstance(version, str):
                found.append(Dependency("nuget", name, version, relative))
    return found


def _gemfile_lock(path: Path, relative: str) -> list[Dependency]:
    found = []
    in_specs = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "specs:":
            in_specs = True
            continue
        if line and not line.startswith(" "):
            in_specs = False
        match = GEM_SPEC.match(line) if in_specs else None
        if match:
            found.append(Dependency("rubygems", match.group(1), match.group(2), relative))
    return found


def _xml_dependencies(path: Path, relative: str, ecosystem: str) -> list[Dependency]:
    root = ET.parse(path).getroot()
    found = []
    for element in root.iter():
        if element.tag.split("}")[-1] == "PackageReference":
            name = element.attrib.get("Include") or element.attrib.get("Update")
            version = element.attrib.get("Version")
            if version is None:
                version_element = next(
                    (child for child in element if child.tag.split("}")[-1] == "Version"), None
                )
                version = version_element.text if version_element is not None else None
            if name and version:
                found.append(Dependency(ecosystem, name, version, relative, "declared"))
        elif element.tag.split("}")[-1] == "dependency":
            values = {
                child.tag.split("}")[-1]: child.text
                for child in element
                if child.tag.split("}")[-1] in {"groupId", "artifactId", "version"}
            }
            artifact, version = values.get("artifactId"), values.get("version")
            if artifact and version:
                name = f"{values.get('groupId', '')}:{artifact}".lstrip(":")
                found.append(Dependency(ecosystem, name, version, relative, "declared"))
    return found


PARSERS: dict[str, tuple[str, Callable[[Path, str], list[Dependency]]]] = {
    "requirements.txt": ("pypi", _requirements),
    "package-lock.json": ("npm", _package_lock),
    "packages.lock.json": ("nuget", _nuget_packages_lock),
    "go.mod": ("go", _go_mod),
    "pyproject.toml": ("pypi", _toml),
    "poetry.lock": ("pypi", _toml),
    "composer.lock": ("composer", _composer_lock),
    "gemfile.lock": ("rubygems", _gemfile_lock),
    "pom.xml": ("maven", lambda path, relative: _xml_dependencies(path, relative, "maven")),
}


def is_supported_manifest(path: Path) -> bool:
    return path.name.lower() in PARSERS or path.suffix.lower() == ".csproj"


def _canonical_package_name(ecosystem: str, name: str) -> str:
    if ecosystem == "pypi":
        return re.sub(r"[-_.]+", "-", name).lower()
    if ecosystem == "nuget":
        return name.casefold()
    return name


def discover_dependencies(
    root: Path, include_errors: bool = False
) -> list[Dependency] | tuple[list[Dependency], list[str]]:
    dependencies: set[Dependency] = set()
    errors: list[str] = []
    for entry in discover_files(root, include_hidden=True):
        parser_entry = PARSERS.get(Path(entry.relative_path).name.lower())
        if not is_supported_manifest(entry.path):
            continue
        parser: Callable[[Path, str], list[Dependency]]
        if entry.path.suffix.lower() == ".csproj":
            parser = lambda path, relative: _xml_dependencies(path, relative, "nuget")
        else:
            assert parser_entry is not None
            _, parser = parser_entry
        try:
            if entry.path.stat().st_size > MAX_MANIFEST_BYTES:
                errors.append(f"{entry.relative_path}: manifest exceeds size limit")
                continue
            dependencies.update(parser(entry.path, entry.relative_path))
        except (
            OSError,
            ValueError,
            TypeError,
            ET.ParseError,
            tomllib.TOMLDecodeError,
        ) as exc:
            errors.append(f"{entry.relative_path}: unable to parse manifest ({type(exc).__name__})")
    records_by_coordinate: dict[tuple[str, str, str, str], tuple[set[str], set[str]]] = {}
    for dependency in dependencies:
        coordinate = (
            dependency.ecosystem,
            _canonical_package_name(dependency.ecosystem, dependency.name),
            dependency.version,
            dependency.version_kind,
        )
        source_paths, display_names = records_by_coordinate.setdefault(coordinate, (set(), set()))
        source_paths.add(dependency.source_path)
        display_names.add(dependency.name)
    result: list[Dependency] = []
    for (ecosystem, _, version, version_kind), (
        source_paths,
        display_names,
    ) in records_by_coordinate.items():
        sources = tuple(sorted(source_paths))
        name = min(display_names, key=lambda value: (value.casefold(), value))
        result.append(
            Dependency(
                ecosystem=ecosystem,
                name=name,
                version=version,
                source_path=sources[0],
                version_kind=version_kind,
                source_paths=sources,
            )
        )
    result.sort(
        key=lambda dependency: (
            dependency.ecosystem.casefold(),
            dependency.name.casefold(),
            dependency.version,
            dependency.version_kind,
        )
    )
    if include_errors:
        return result, errors
    return result
