from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .commands_publish_copy import copy_publishables, write_publish_manifest
from .docs_bridge import run_doc_wizard
from .git_io import write_json
from .publish_report import build_publish_report


def publish_review_required_payload(
    report: dict[str, Any],
    rewrite_result: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload = {
        "command": "publish",
        "status": "review-required",
        **report,
        "doc_rewrite_result": rewrite_result,
        "error": (
            "Public docs were auto-rewritten. Review the changes, then rerun publish "
            "with --approve-doc-review."
        ),
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload


def execute_publish(
    repo_root: Path,
    report: dict[str, Any],
    rewrite_result: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    snapshot_dir = Path(report["snapshot_dir"])
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    manifest_rows = copy_publishables(report, snapshot_dir)
    manifest_path, manifest = write_publish_manifest(repo_root, report, snapshot_dir, manifest_rows)
    payload = {
        "command": "publish",
        "status": "ok",
        **report,
        "doc_rewrite_result": rewrite_result,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload


def maybe_rewrite_docs(
    repo_root: Path,
    report: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rewrite_result: dict[str, Any] = {"changed_files": 0, "rewrites": [], "write": False}
    if not report["requires_doc_review"]:
        return report, rewrite_result
    rewrite_result = run_doc_wizard(repo_root, "sanitize-public-docs", "--write")
    report = build_publish_report(repo_root, args.snapshot_id)
    return report, rewrite_result
