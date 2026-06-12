from __future__ import annotations

from pathlib import Path
from typing import Any

from .bundle_common import DEFAULT_FLOW
from .inventory_declared import collect_declared_paths, missing_declared_path_findings
from .inventory_scan import scan_repo_artifacts
from .peers import peer_plugin_script
from .workspace import append_workspace_findings, classify_workspace_topology, default_workspace_path_review
from .workspace_handoff import add_unique_action, run_workspace_governor_dry_run

WORKSPACE_GOVERNOR_SCRIPT = peer_plugin_script("workspace-governor", "workspace_governor.py")


def build_generic_workspace_path_review(evidence: list[str]) -> dict[str, Any]:
    summary = default_workspace_path_review("not-needed")
    summary["source"] = "generic-repo heuristic"
    summary["topology_evidence"] = evidence
    return summary


def inventory_repo(root: Path, *, workspace_handoff=run_workspace_governor_dry_run) -> dict[str, Any]:
    project_doc = root / "AGENTS.md"
    registry = root / "analysis_registry.yaml"
    scripts, notebooks, data_dirs = scan_repo_artifacts(root)
    declared_paths = collect_declared_paths(project_doc, registry)
    findings = missing_declared_path_findings(declared_paths)

    recommended_actions: list[str] = []
    if findings:
        add_unique_action(recommended_actions, "Resolve missing declared paths before running specialist review lanes.")
    topology_mode, topology_confidence, topology_evidence, should_run_workspace_handoff = classify_workspace_topology(
        root,
        declared_paths,
        findings,
        project_doc.exists(),
        registry.exists(),
        scripts,
        notebooks,
        data_dirs,
    )
    workspace_path_review = build_generic_workspace_path_review(topology_evidence)
    workspace_path_review["topology_mode"] = topology_mode
    workspace_path_review["topology_confidence"] = topology_confidence
    if should_run_workspace_handoff:
        workspace_review = workspace_handoff(root, WORKSPACE_GOVERNOR_SCRIPT)
        workspace_path_review = workspace_review["summary"]
        workspace_path_review["topology_mode"] = topology_mode
        workspace_path_review["topology_confidence"] = topology_confidence
        workspace_path_review["topology_evidence"] = topology_evidence
        append_workspace_findings(findings, recommended_actions, workspace_review)
    if not findings and not recommended_actions:
        add_unique_action(recommended_actions, "Proceed to specialist review lanes.")

    return {
        "scope": "analysis-review-preflight",
        "artifact_map": {
            "repo_root": str(root),
            "project_doc": str(project_doc) if project_doc.exists() else None,
            "analysis_registry": str(registry) if registry.exists() else None,
            "scripts_and_tests": sorted(scripts),
            "notebooks": sorted(notebooks),
            "data_like_dirs": sorted(data_dirs),
            "declared_paths": declared_paths,
            "workspace_path_review": workspace_path_review,
        },
        "findings": findings,
        "direct_evidence_vs_inference": (
            "Inventory findings are grounded in the repo tree and declared project metadata."
        ),
        "required_tests_checks": [
            "Confirm that declared runtime and published-output paths match the actual environment.",
        ],
        "recommended_actions": recommended_actions,
        "flow": DEFAULT_FLOW,
    }
