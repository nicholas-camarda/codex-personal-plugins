from __future__ import annotations

import argparse


def add_ops_parsers(subparsers: argparse._SubParsersAction) -> None:
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
