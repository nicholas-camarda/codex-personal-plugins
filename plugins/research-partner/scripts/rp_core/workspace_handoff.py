from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .workspace_roots import WORKSPACE_SOURCE_NAME
from .workspace_topology import default_workspace_path_review


def add_unique_action(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


def run_workspace_governor_dry_run(root: Path, workspace_governor_script: Path) -> dict[str, Any]:
    summary = default_workspace_path_review("unavailable")
    summary["source"] = WORKSPACE_SOURCE_NAME
    if not workspace_governor_script.exists():
        return {"summary": summary, "status": "unavailable", "payload": None}

    try:
        proc = subprocess.run(
            [sys.executable, str(workspace_governor_script), "dry-run", "--repo", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise ValueError("workspace-governor returned a non-object payload")
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError, ValueError):
        summary["status"] = "error"
        return {"summary": summary, "status": "error", "payload": None}

    summary.update(
        {
            "status": "ok",
            "proposed_code_root": payload.get("proposed_code_root"),
            "proposed_runtime_root": payload.get("proposed_runtime_root"),
            "proposed_cloud_home": payload.get("proposed_cloud_home"),
            "doc_contract_passed": payload.get("doc_contract", {}).get("passed"),
            "rewrite_candidate_count": len(payload.get("rewrite_candidates", [])),
            "question_count": len(payload.get("questions", [])),
        }
    )
    return {"summary": summary, "status": "ok", "payload": payload}


def append_workspace_findings(
    findings: list[dict[str, Any]],
    recommended_actions: list[str],
    workspace_review: dict[str, Any],
) -> None:
    status = workspace_review["summary"]["status"]
    payload = workspace_review["payload"] or {}

    if status in {"error", "unavailable"}:
        findings.append(
            {
                "title": "Workspace audit evidence unavailable",
                "severity": "P2",
                "evidence_basis": "Missing",
                "message": "The workspace-governor dry-run handoff did not produce usable path-topology evidence.",
            }
        )
        add_unique_action(
            recommended_actions,
            "Restore workspace-governor dry-run evidence before trusting workspace path assumptions.",
        )
        return

    handoff_checks = [
        (
            bool(payload.get("questions")),
            {
                "title": "Workspace topology remains unresolved",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run reported unresolved workspace questions that should be "
                    "answered before specialist review relies on path assumptions."
                ),
            },
            "Review the workspace-governor dry-run questions before running specialist review lanes.",
        ),
        (
            payload.get("doc_contract", {}).get("passed") is False,
            {
                "title": "Public/private doc contract is incomplete",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run found that the repo does not fully satisfy the "
                    "README plus AGENTS.md documentation split."
                ),
            },
            "Fix the README and AGENTS.md doc contract before relying on published path guidance.",
        ),
        (
            bool(payload.get("rewrite_candidates")),
            {
                "title": "Stale hard-coded path assumptions detected",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run found path rewrite candidates that may invalidate "
                    "implementation or methods assumptions."
                ),
            },
            "Review workspace-governor rewrite candidates before interpreting path-sensitive outputs.",
        ),
    ]
    for should_add, finding, action in handoff_checks:
        if not should_add:
            continue
        findings.append(finding)
        add_unique_action(recommended_actions, action)
