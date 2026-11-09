"""Command-line interface for CodeScan."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from codescan import __version__
from codescan.scan import write_scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codescan", description="Assess a software project.")
    parser.add_argument("--version", action="version", version=f"codescan {__version__}")
    commands = parser.add_subparsers(dest="command")
    scan = commands.add_parser("scan", help="scan a local project folder")
    scan.add_argument("path", metavar="PATH", type=Path, help="project folder to scan")
    scan.add_argument("--output", type=Path, help="directory for generated report artifacts")
    scan.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="relative file pattern to exclude (repeatable)",
    )
    scan.add_argument(
        "--include-hidden", action="store_true", help="include files in hidden folders"
    )
    scan.add_argument("--force", action="store_true", help="overwrite existing CodeScan artifacts")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    if args.command == "scan":
        if not args.path.exists():
            print(f"codescan: path does not exist: {args.path}", file=sys.stderr)
            return 2
        if not args.path.is_dir():
            print(f"codescan: path is not a directory: {args.path}", file=sys.stderr)
            return 2
        output = args.output or (args.path / "codescan-output")
        try:
            write_scan(args.path, output, tuple(args.exclude), args.include_hidden, args.force)
        except FileExistsError as exc:
            print(f"codescan: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"codescan: unable to write scan output: {exc}", file=sys.stderr)
            return 1
        print(f"CodeScan report written to {output.resolve()}")
        return 0
    parser.print_help()
    return 0


def entrypoint() -> None:
    raise SystemExit(main())
