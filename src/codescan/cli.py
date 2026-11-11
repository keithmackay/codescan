"""Command-line interface for CodeScan."""

from __future__ import annotations

import argparse
import csv
import getpass
import io
import sys
from collections.abc import Sequence
from pathlib import Path

from codescan import __version__
from codescan.identity_crypto import decrypt_identity_map
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
        help="relative glob pattern to exclude; ** spans directories and backslashes are normalized (repeatable)",
    )
    scan.add_argument(
        "--include-hidden", action="store_true", help="include files in hidden folders"
    )
    scan.add_argument("--force", action="store_true", help="overwrite existing CodeScan artifacts")
    scan.add_argument(
        "--encrypt-developer-identities",
        action="store_true",
        help="prompt for a seed and include pseudonymous developer tracking plus an encrypted identity map",
    )
    scan.add_argument(
        "--vulnerability-scan",
        choices=("disabled", "offline", "online"),
        default="disabled",
        help="use OSV-Scanner; online explicitly sends dependency metadata to OSV.dev",
    )
    scan.add_argument(
        "--osv-scanner",
        default="osv-scanner",
        help="OSV-Scanner executable name or path (default: osv-scanner on PATH)",
    )
    scan.add_argument(
        "--license-scan",
        action="store_true",
        help="use OSV-Scanner license metadata from deps.dev (requires --vulnerability-scan online)",
    )
    decrypt = commands.add_parser(
        "decrypt-identities", help="decrypt an encrypted developer identity map to CSV on stdout"
    )
    decrypt.add_argument("file", type=Path, help="developer-identities.enc.json file")
    return parser


def _prompt_seed(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise RuntimeError("seed entry requires an interactive terminal")
    return getpass.getpass(prompt)


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
        identity_seed = None
        if args.encrypt_developer_identities:
            try:
                identity_seed = _prompt_seed("Encryption seed: ")
                confirmation = _prompt_seed("Confirm encryption seed: ")
            except RuntimeError as exc:
                print(f"codescan: {exc}", file=sys.stderr)
                return 2
            if identity_seed != confirmation:
                print("codescan: seeds did not match", file=sys.stderr)
                return 2
        if args.vulnerability_scan == "online":
            print(
                "Online vulnerability scanning sends package names, versions, and ecosystems "
                "to OSV.dev; OSV-Scanner may contact documented supporting services.",
                file=sys.stderr,
            )
        if args.license_scan and args.vulnerability_scan != "online":
            print(
                "codescan: --license-scan requires --vulnerability-scan online because OSV-Scanner retrieves license metadata from deps.dev",
                file=sys.stderr,
            )
            return 2
        if args.license_scan:
            print(
                "Package license metadata is retrieved through deps.dev; review identifiers with appropriate legal counsel.",
                file=sys.stderr,
            )
        try:
            write_scan(
                args.path,
                output,
                tuple(args.exclude),
                args.include_hidden,
                args.force,
                identity_seed,
                None if args.vulnerability_scan == "disabled" else args.vulnerability_scan,
                args.osv_scanner,
                args.license_scan,
            )
        except FileExistsError as exc:
            print(f"codescan: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"codescan: unable to write scan output: {exc}", file=sys.stderr)
            return 1
        print(f"CodeScan report written to {output.resolve()}")
        return 0
    if args.command == "decrypt-identities":
        try:
            seed = _prompt_seed("Decryption seed: ")
        except RuntimeError as exc:
            print(f"codescan: {exc}", file=sys.stderr)
            return 2
        try:
            encrypted = args.file.read_text(encoding="utf-8")
            identities = decrypt_identity_map(encrypted, seed)
        except (OSError, ValueError) as exc:
            print(f"codescan: {exc}", file=sys.stderr)
            return 2
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            ["developer_id", "name", "email", "commits", "files_changed", "additions", "deletions"]
        )
        for identifier, identity in sorted(identities.items()):
            writer.writerow(
                [
                    identifier,
                    identity.get("name", ""),
                    identity.get("email", ""),
                    identity.get("commits", ""),
                    identity.get("files_changed", ""),
                    identity.get("additions", ""),
                    identity.get("deletions", ""),
                ]
            )
        sys.stdout.write(buffer.getvalue())
        return 0
    parser.print_help()
    return 0


def entrypoint() -> None:
    raise SystemExit(main())
