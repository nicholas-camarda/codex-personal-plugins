#!/usr/bin/env python3
"""Helper CLI for research-partner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rp_core.bundles import bundle_review
from rp_core.inventory import inventory_repo as _inventory_repo
from rp_core.lanes import run_review as run_review_impl
from rp_core.peers import peer_plugin_root, peer_plugin_script
from rp_core.validate_bundle import validate_plugin
from rp_core.workspace import (
    default_workspace_path_review,
    parse_declared_path,
    run_workspace_governor_dry_run,
)

EXECUTABLE_LANES = [
    "documentation-wizard",
    "implementation-auditor",
    "stats-reviewer",
    "scientific-reviewer",
    "literature-support-reviewer",
    "robustness-test-designer",
]


def inventory_repo(repo_root: Path) -> dict:
    return _inventory_repo(repo_root, workspace_handoff=run_workspace_governor_dry_run)


def run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None) -> dict:
    return run_review_impl(
        repo_root,
        output_dir,
        lanes,
        executable_lanes=EXECUTABLE_LANES,
        inventory_func=inventory_repo,
        bundle_func=bundle_review,
        documentation_wizard_script=peer_plugin_script("documentation-wizard", "documentation_wizard.py"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="research-partner helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Inventory repo artifacts before review")
    inventory_parser.add_argument("--repo", required=True)

    bundle_parser = subparsers.add_parser("bundle", help="Bundle preflight and lane outputs")
    bundle_parser.add_argument("--preflight", required=True)
    bundle_parser.add_argument("--lane", action="append", default=[])

    run_parser = subparsers.add_parser("run", help="Run preflight, execute review lanes, and bundle results")
    run_parser.add_argument("--repo", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--lane", action="append", default=[])

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    args = parser.parse_args()
    if args.command == "inventory":
        payload = inventory_repo(Path(args.repo).expanduser().resolve())
    elif args.command == "bundle":
        payload = bundle_review(Path(args.preflight).resolve(), [Path(item).resolve() for item in args.lane])
    elif args.command == "run":
        payload = run_review(
            repo_root=Path(args.repo),
            output_dir=Path(args.output_dir),
            lanes=args.lane or None,
        )
    else:
        payload = validate_plugin(Path(__file__).resolve().parent)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
