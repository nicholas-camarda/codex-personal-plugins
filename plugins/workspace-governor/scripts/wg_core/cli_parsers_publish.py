from __future__ import annotations

import argparse
from datetime import datetime


def add_publish_parsers(subparsers: argparse._SubParsersAction) -> None:
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
