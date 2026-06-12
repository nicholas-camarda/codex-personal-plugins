from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _host
from .metadata_profile import infer_project_profile
from .publish_deny import GLOBAL_PUBLISH_DENYLIST
from .publish_map import iter_publish_candidates


def build_publish_report(repo_root: Path, snapshot_id: str) -> dict[str, Any]:
    wg = _host.wg()
    profile = infer_project_profile(repo_root, repo_root.name)
    runtime_root, runtime_source = wg.configured_runtime_home(repo_root)
    cloud_home, cloud_source = wg.configured_cloud_home(repo_root, profile["profile_guess"])
    publish_root_name, publish_root_source = wg.configured_publish_root_name(repo_root)
    publish_layout, publish_layout_source = wg.configured_publish_layout(repo_root)
    publish_denylist, denylist_source = wg.project_publish_denylist(repo_root)
    denylist = [*GLOBAL_PUBLISH_DENYLIST, *publish_denylist]
    snapshot_dir = wg.publish_snapshot_dir(cloud_home, publish_root_name, snapshot_id)
    doc_contract = wg.ensure_dual_doc_contract(repo_root)
    doc_policy = wg.doc_policy_report(repo_root)
    doc_contract_required = profile["profile_guess"] in {"research", "sideproject"}
    if not doc_contract_required:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = False
        doc_contract["passed"] = True
        doc_policy = dict(doc_policy)
        doc_policy["requires_rewrite"] = False
    publish_candidates = iter_publish_candidates(runtime_root, denylist, publish_layout)
    report = {
        "repo_root": str(repo_root),
        "project_slug": wg.normalized_project_slug(repo_root),
        "project_type": profile["profile_guess"],
        "registry_review": profile["metadata"].get("registry_review"),
        "doc_contract": doc_contract,
        "doc_policy": doc_policy,
        "runtime_root": str(runtime_root),
        "runtime_root_source": runtime_source,
        "cloud_home": str(cloud_home),
        "cloud_home_source": cloud_source,
        "publish_root_name": publish_root_name,
        "publish_root_source": publish_root_source,
        "publish_layout": publish_layout,
        "publish_layout_source": publish_layout_source,
        "snapshot_id": snapshot_id,
        "snapshot_dir": str(snapshot_dir),
        "snapshot_exists": snapshot_dir.exists(),
        "publish_policy": {
            "global_denylist": GLOBAL_PUBLISH_DENYLIST,
            "project_override_denylist": publish_denylist,
            "override_source": denylist_source,
            "effective_denylist": denylist,
        },
        "publish_candidates": publish_candidates,
    }
    report["requires_doc_review"] = bool(doc_policy.get("requires_rewrite")) and doc_contract_required
    report["publish_destination_checks"] = wg.collect_publish_destination_checks(report)
    return report
