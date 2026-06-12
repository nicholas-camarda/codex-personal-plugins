from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .commands_publish_blocked import publish_blocked_errors, publish_failure_payload
from .commands_publish_execute import execute_publish, maybe_rewrite_docs, publish_review_required_payload
from .git_io import write_json
from .publish_report import build_publish_report


def publish_preview(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    payload = {
        "command": "publish-preview",
        "status": "ok",
        **report,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload


def publish(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    if report["project_type"] in {"research", "sideproject"} and not report["doc_contract"]["passed"]:
        return publish_failure_payload(
            "publish",
            report,
            "Dual-doc contract failed. README and AGENTS.md must both exist before publish.",
            args,
        )

    blocked_error = publish_blocked_errors(report)
    if blocked_error is not None:
        return publish_failure_payload("publish", report, blocked_error, args)

    report, rewrite_result = maybe_rewrite_docs(repo_root, report, args)
    changed_files = rewrite_result.get("changed_files", 0)
    if changed_files > 0 and not args.approve_doc_review:
        return publish_review_required_payload(report, rewrite_result, args)

    return execute_publish(repo_root, report, rewrite_result, args)
