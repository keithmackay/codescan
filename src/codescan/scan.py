"""Local scan orchestration and artifact writing."""

from __future__ import annotations

import uuid
from pathlib import Path

from codescan.analyzers.inventory import FileInventory, inventory_file
from codescan.discovery import discover_files
from codescan.renderers.csv import render_inventory_csv
from codescan.renderers.json import render_results
from codescan.renderers.markdown import render_report

OUTPUT_FILES = ("report.md", "files.csv", "results.json")


def collect_inventory(
    root: Path, excludes: tuple[str, ...] = (), include_hidden: bool = False
) -> list[FileInventory]:
    files = discover_files(root, excludes=excludes, include_hidden=include_hidden)
    inventory: list[FileInventory] = []
    for discovered in files:
        try:
            inventory.append(inventory_file(discovered.path, root.resolve()))
        except OSError:
            # An unreadable file is omitted from the inventory for now; surfaced in the report in a later slice.
            continue
    return inventory


def write_scan(
    root: Path,
    output: Path,
    excludes: tuple[str, ...] = (),
    include_hidden: bool = False,
    force: bool = False,
) -> None:
    root = root.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUT_FILES if (output / name).exists()]
    if existing and not force:
        raise FileExistsError(
            f"output already contains CodeScan artifacts: {', '.join(existing)} (use --force)"
        )
    items = collect_inventory(root, excludes=excludes, include_hidden=include_hidden)
    root_label = root.name or root.anchor
    artifacts = {
        "report.md": render_report(root_label, items),
        "files.csv": render_inventory_csv(items),
        "results.json": render_results(root_label, items, str(uuid.uuid4())),
    }
    for name, content in artifacts.items():
        destination = output / name
        temporary = output / f".{name}.tmp"
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(destination)
