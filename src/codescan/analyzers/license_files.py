"""Detect root-level project license and notice files without interpreting legal terms."""

from __future__ import annotations

from pathlib import Path

from codescan.models import Evidence, Finding

LICENSE_NAMES = {
    "license",
    "license.txt",
    "license.md",
    "copying",
    "copying.txt",
    "notice",
    "notice.txt",
}


def analyze_license_files(root: Path) -> list[Finding]:
    detected = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_file() and path.name.casefold() in LICENSE_NAMES
        ),
        key=lambda path: path.name.casefold(),
    )
    if detected:
        return [
            Finding(
                id="LICENSE-FILE-001",
                category="licensing",
                title="License files detected",
                summary=f"Detected {len(detected)} root-level license or notice file(s).",
                evidence=[Evidence(kind="license_file", path=path.name) for path in detected],
                limitations=[
                    "File presence does not determine the applicable license, completeness, compatibility, or legal risk."
                ],
            )
        ]
    return [
        Finding(
            id="LICENSE-FILE-NOTDETECTED-001",
            category="licensing",
            title="License file not detected",
            summary="No common root-level LICENSE, COPYING, or NOTICE file was detected.",
            limitations=[
                "License terms may be declared in another file or external policy; this is not a legal conclusion."
            ],
        )
    ]
