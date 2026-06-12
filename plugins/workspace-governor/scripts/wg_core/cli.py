from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .commands_assess import assess
from .commands_audit import audit, dry_run
from .commands_publish import publish, publish_preview
from .plugin_validate import validate_plugin
from .verification import apply_plan, verify_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace governor helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    apply_parser = subparsers.add_parser("apply", help="Apply a move plan from an audit or assess JSON file")
    apply_parser.add_argument(
        "--audit",
        required=True,
        help="Audit or assess JSON produced by the audit or assess command",
    )
    apply_parser.add_argument("--backup-root", help="Backup root directory")
    apply_parser.add_argument("--output", help="Write apply manifest JSON to this path")

    verify_parser = subparsers.add_parser("verify", help="Verify a move manifest")
    verify_parser.add_argument("--manifest", required=True, help="Apply manifest JSON produced by apply")
    verify_parser.add_argument("--deep", action="store_true", help="Use content hashes for verification")
    verify_parser.add_argument(
        "--test-command",
        nargs=argparse.REMAINDER,
        help="Optional command to run in each destination after verification metadata checks",
    )
    verify_parser.add_argument("--output", help="Write verification JSON to this path")

    preview_parser = subparsers.add_parser(
        "publish-preview",
        help="Preview publishable runtime artifacts and doc policy checks",
    )
    preview_parser.add_argument("--repo", required=True, help="Path to the repository to inspect")
    preview_parser.add_argument(
        "--snapshot-id",
        default=format(datetime.now().date(), "%Y-%m-%d"),
        help="Snapshot identifier for the cloud publish folder",
    )
    preview_parser.add_argument("--output", help="Write publish preview JSON to this path")

    publish_parser = subparsers.add_parser("publish", help="Publish runtime artifacts into a dated cloud snapshot")
    publish_parser.add_argument("--repo", required=True, help="Path to the repository to publish")
    publish_parser.add_argument(
        "--snapshot-id",
        default=format(datetime.now().date(), "%Y-%m-%d"),
        help="Snapshot identifier for the cloud publish folder",
    )
    publish_parser.add_argument(
        "--approve-doc-review",
        action="store_true",
        help="Acknowledge review after any auto-rewritten public docs",
    )
    publish_parser.add_argument("--output", help="Write publish JSON to this path")

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    return parser


def _validate_command(_args: argparse.Namespace) -> dict[str, Any]:
    scripts_dir = Path(__file__).resolve().parents[1]
    return validate_plugin(scripts_dir)


def _verify_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.test_command and args.test_command[:1] == ["--"]:
        args.test_command = args.test_command[1:]
    return verify_manifest(args)


_COMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "assess": assess,
    "audit": audit,
    "dry-run": dry_run,
    "apply": apply_plan,
    "publish-preview": publish_preview,
    "publish": publish,
    "verify": _verify_command,
    "validate": _validate_command,
}


def command_payload(args: argparse.Namespace) -> dict[str, Any]:
    handler = _COMMAND_HANDLERS.get(args.command)
    if handler is None:
        raise ValueError(f"Unsupported command: {args.command}")
    return handler(args)
