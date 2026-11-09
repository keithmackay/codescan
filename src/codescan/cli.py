"""Command-line interface for CodeScan."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from codescan import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codescan", description="Assess a software project.")
    parser.add_argument("--version", action="version", version=f"codescan {__version__}")
    commands = parser.add_subparsers(dest="command")
    scan = commands.add_parser("scan", help="scan a local project folder")
    scan.add_argument("path", metavar="PATH", type=Path, help="project folder to scan")
    scan.add_argument("--output", type=Path, help="directory for generated report artifacts")
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
        print("CodeScan scan engine is not implemented yet.", file=sys.stderr)
        return 1
    parser.print_help()
    return 0


def entrypoint() -> None:
    raise SystemExit(main())
