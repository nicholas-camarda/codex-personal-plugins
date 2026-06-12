from __future__ import annotations

import argparse
from datetime import datetime


def add_repo_parsers(subparsers: argparse._SubParsersAction) -> None:
    assess_parser = subparsers.add_parser("assess", help="Run the full non-mutating assessment pass for one repo")
    assess_parser.add_argument("--repo", required=True, help="Path to the repository to assess")
    assess_parser.add_argument("--kind", help="Optional override: research, sideproject, or general")
    assess_parser.add_argument(
        "--classify",
        action="append",
        help="Explicit classification, e.g. project=sideproject or project=research",
    )
    assess_parser.add_argument(
        "--roots",
        nargs="*",
        help="Roots to scan for workspace-wide planning context; defaults to canonical and legacy roots",
    )
    assess_parser.add_argument(
        "--snapshot-id",
        default=format(datetime.now().date(), "%Y-%m-%d"),
        help="Snapshot identifier for the cloud publish folder",
    )
    assess_parser.add_argument("--output", help="Write assessment JSON to this path")

    dry_run_parser = subparsers.add_parser(
        "dry-run",
        help="Inspect one repo and list the questions needed to migrate it safely",
    )
    dry_run_parser.add_argument("--repo", required=True, help="Path to the repository to inspect")
    dry_run_parser.add_argument("--kind", help="Optional override: research, sideproject, or general")
    dry_run_parser.add_argument(
        "--classify",
        action="append",
        help="Explicit classification, e.g. project=sideproject or project=research",
    )
    dry_run_parser.add_argument("--output", help="Write dry-run JSON to this path")

    audit_parser = subparsers.add_parser("audit", help="Inventory roots and build a move plan")
    audit_parser.add_argument("--roots", nargs="*", help="Roots to scan; defaults to the canonical and legacy roots")
    audit_parser.add_argument(
        "--classify",
        action="append",
        help="Explicit classification, e.g. project=sideproject or project=research",
    )
    audit_parser.add_argument("--output", help="Write audit JSON to this path")
