#!/usr/bin/env python3
"""Helper CLI for documentation-wizard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dw_core.files import iter_files
from dw_core.interfaces import extract_interfaces
from dw_core.plugin_validate import validate_plugin
from dw_core.reporting import build_regression_check, build_report, inventory_docs
from dw_core.sanitize import sanitize_public_docs

# Compatibility exports for tests and downstream imports.
__all__ = [
    "build_report",
    "extract_interfaces",
    "inventory_docs",
    "iter_files",
    "sanitize_public_docs",
    "validate_plugin",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="documentation-wizard helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser(
        "inventory",
        help="List documentation surfaces and source-of-truth candidates",
    )
    inventory_parser.add_argument("--repo", required=True)

    interfaces_parser = subparsers.add_parser(
        "interfaces",
        help="Extract live CLI flags, config keys, and referenced paths",
    )
    interfaces_parser.add_argument("--repo", required=True)

    report_parser = subparsers.add_parser("report", help="Generate a documentation drift report")
    report_parser.add_argument("--repo", required=True)

    regression_parser = subparsers.add_parser("regression-check", help="Generate a lightweight regression check")
    regression_parser.add_argument("--repo", required=True)
    regression_parser.add_argument(
        "--kind",
        required=True,
        choices=["cli-flags", "config-schema", "referenced-paths", "private-infra"],
    )

    sanitize_parser = subparsers.add_parser(
        "sanitize-public-docs",
        help="Rewrite public docs to remove maintainer-specific infrastructure details",
    )
    sanitize_parser.add_argument("--repo", required=True)
    sanitize_parser.add_argument("--write", action="store_true", help="Apply the sanitized rewrites to disk")

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    args = parser.parse_args()
    if args.command == "validate":
        payload = validate_plugin(Path(__file__).resolve().parent)
    else:
        root = Path(args.repo).expanduser().resolve()
        if args.command == "inventory":
            payload = inventory_docs(root)
        elif args.command == "interfaces":
            payload = extract_interfaces(root)
        elif args.command == "report":
            payload = build_report(root)
        elif args.command == "sanitize-public-docs":
            payload = sanitize_public_docs(root, write=bool(args.write))
        else:
            kind_map = {
                "cli-flags": "cli-flags",
                "config-schema": "stale-config-key",
                "referenced-paths": "broken-referenced-path",
                "private-infra": "private-infra-leak",
            }
            payload = build_regression_check(root, kind_map[args.kind])
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
