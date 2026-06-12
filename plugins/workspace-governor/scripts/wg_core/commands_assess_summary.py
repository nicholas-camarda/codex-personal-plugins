from __future__ import annotations

from typing import Any


def assessment_outcome(
    workspace_move_count: int,
    dry_run_rewrite_count: int,
    publish_requires_doc_review: bool | None,
    doc_contract_passed: bool | None,
) -> tuple[str, str]:
    if workspace_move_count > 0:
        return "workspace-moves-planned", "review move plan before apply"
    if dry_run_rewrite_count > 0:
        return "rewrite-review-needed", "review rewrite candidates; no workspace apply is needed"
    if publish_requires_doc_review:
        return "publish-doc-review-needed", "review public-doc sanitization findings; no workspace apply is needed"
    if not doc_contract_passed:
        return "doc-contract-missing", "add missing README or AGENTS.md before publish; no workspace apply is needed"
    return "no-migration-work-planned", "no workspace apply is needed"


def related_audit_records(
    audit_report: dict[str, Any],
    repo_slug: str,
    repo_root: str,
    dry_run_report: dict[str, Any],
) -> list[dict[str, Any]]:
    proposed = {
        dry_run_report.get("proposed_destination"),
        dry_run_report.get("proposed_code_root"),
    }
    return [
        record
        for record in audit_report["records"]
        if record.get("slug") == repo_slug
        or record.get("source") == repo_root
        or record.get("destination") in proposed
    ]
