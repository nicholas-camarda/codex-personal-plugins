from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .classify import parse_classifications, parse_repo_kind
from .commands_assess_summary import assessment_outcome, related_audit_records
from .commands_audit import audit
from .git_io import write_json
from .metadata_profile import infer_project_profile
from .paths import now_stamp, normalized_project_slug
from .planning import build_dry_run_plan
from .publish_report import build_publish_report
from .roots import DEFAULT_SCAN_ROOTS


def assess(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")

    classifications = parse_classifications(args.classify or [])
    profile = infer_project_profile(repo_root, repo_root.name)
    if args.kind:
        profile["profile_guess"] = parse_repo_kind(args.kind)

    dry_run_report = build_dry_run_plan(repo_root, profile, classifications)

    default_roots = [str(root) for root in DEFAULT_SCAN_ROOTS]
    audit_roots = [Path(root).expanduser().resolve() for root in (args.roots or default_roots)]
    audit_report = audit(
        argparse.Namespace(
            roots=[str(root) for root in audit_roots],
            classify=args.classify or [],
            output=None,
        )
    )

    publish_report = build_publish_report(repo_root, args.snapshot_id)
    publish_preview_report = {
        "command": "publish-preview",
        "status": "ok",
        **publish_report,
    }

    repo_slug = normalized_project_slug(repo_root)
    related_records = related_audit_records(audit_report, repo_slug, str(repo_root), dry_run_report)
    workspace_plan = audit_report.get("plan", [])
    workspace_move_count = len(workspace_plan) if isinstance(workspace_plan, list) else 0
    dry_run_rewrite_count = len(dry_run_report.get("rewrite_candidates", []))
    doc_contract_passed = dry_run_report.get("doc_contract", {}).get("passed")
    publish_requires_doc_review = publish_preview_report.get("requires_doc_review")
    assessment_outcome_value, next_step = assessment_outcome(
        workspace_move_count,
        dry_run_rewrite_count,
        publish_requires_doc_review,
        doc_contract_passed,
    )

    payload = {
        "command": "assess",
        "status": "ok",
        "generated_at": now_stamp(),
        "repo_root": str(repo_root),
        "repo_slug": repo_slug,
        "dry_run": dry_run_report,
        "audit": audit_report,
        "related_audit_records": related_records,
        "publish_preview": publish_preview_report,
        "summary": {
            "dry_run_question_count": len(dry_run_report.get("questions", [])),
            "dry_run_rewrite_candidate_count": dry_run_rewrite_count,
            "doc_contract_passed": doc_contract_passed,
            "publish_requires_doc_review": publish_requires_doc_review,
            "publishable_candidate_count": len(
                publish_preview_report.get("publish_candidates", {}).get("publishable", [])
            ),
            "skipped_publish_candidate_count": len(
                publish_preview_report.get("publish_candidates", {}).get("skipped", [])
            ),
            "related_workspace_record_count": len(related_records),
            "workspace_move_count": workspace_move_count,
            "apply_recommended": workspace_move_count > 0,
            "assessment_outcome": assessment_outcome_value,
            "next_step": next_step,
        },
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload
