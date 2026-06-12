from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _host
from .planning_classify import classify_candidate as classify_candidate
from .publish_deny import GLOBAL_PUBLISH_DENYLIST
from .roots import PROJECTS_ROOT


def build_dry_run_plan(
    repo_root: Path,
    profile: dict[str, Any],
    classifications: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    wg = _host.wg()
    classification = (classifications or {}).get(wg.slugify(repo_root.name))
    destination = wg.suggested_destination(repo_root.name, profile, classification)
    runtime_home, runtime_source = wg.configured_runtime_home(repo_root)
    cloud_home, cloud_source = wg.configured_cloud_home(repo_root, profile["profile_guess"])
    publish_root_name, publish_root_source = wg.configured_publish_root_name(repo_root)
    denylist_overrides, denylist_source = wg.project_publish_denylist(repo_root)
    doc_contract = wg.ensure_dual_doc_contract(repo_root)
    doc_contract_required = profile["profile_guess"] in {"research", "sideproject"}
    if not doc_contract_required:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = False
        doc_contract["passed"] = True
        doc_contract["message"] = "Dual-doc contract is advisory for general software repos."
    else:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = True
    question_profile = dict(profile)
    question_profile["current_root_kind"] = wg.immediate_root_label(repo_root)
    return {
        "command": "dry-run",
        "status": "ok",
        "repo_root": str(repo_root),
        "current_root_kind": wg.immediate_root_label(repo_root),
        "profile_guess": profile["profile_guess"],
        "research_domain": profile.get("research_domain"),
        "confidence": profile["confidence"],
        "profile_reason": profile["profile_reason"],
        "metadata": profile["metadata"],
        "existing_footprints": profile["existing_footprints"],
        "proposed_destination": str(destination) if destination else None,
        "proposed_code_root": str(PROJECTS_ROOT / wg.normalized_project_slug(repo_root)),
        "proposed_runtime_root": str(runtime_home),
        "proposed_cloud_home": str(cloud_home),
        "publish_root_name": publish_root_name,
        "publish_root_source": publish_root_source,
        "runtime_root_source": runtime_source,
        "cloud_home_source": cloud_source,
        "doc_contract": doc_contract,
        "publish_policy": {
            "global_denylist": GLOBAL_PUBLISH_DENYLIST,
            "project_override_denylist": denylist_overrides,
            "override_source": denylist_source,
        },
        "registry_review": profile["metadata"].get("registry_review"),
        "rewrite_candidates": wg.rewrite_candidates(repo_root, destination),
        "questions": wg.build_dry_run_questions(question_profile, destination),
        "signals": profile,
    }


def build_audit_payload(
    roots: list[Path],
    classifications: dict[str, dict[str, str]],
    records: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    plan = [record for record in records if record["action"] == "move" and record["destination"]]
    rewrite_plan = [
        {
            "source": record["source"],
            "destination": record["destination"],
            "rewrite_candidates": record["rewrite_candidates"],
        }
        for record in plan
        if record.get("rewrite_candidates")
    ]
    return {
        "command": "audit",
        "status": "ok",
        "generated_at": generated_at,
        "roots": [str(root) for root in roots],
        "classifications": classifications,
        "records": records,
        "plan": plan,
        "skipped": [record for record in records if record["action"] != "move"],
        "rewrite_plan": rewrite_plan,
    }
