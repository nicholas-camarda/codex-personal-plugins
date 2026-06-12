from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
ONEDRIVE_ROOT = Path(
    os.environ.get("CODEX_ONEDRIVE_ROOT", HOME / "Library" / "CloudStorage" / "OneDrive-Personal")
).expanduser()
PROJECTS_ROOT = Path(os.environ.get("CODEX_PROJECTS_ROOT", HOME / "Projects")).expanduser()
RUNTIME_ROOT = Path(os.environ.get("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")).expanduser()
RESEARCH_ROOT = Path(os.environ.get("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")).expanduser()
SIDEPROJECTS_ROOT = Path(os.environ.get("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")).expanduser()
LEGACY_ROOT = Path(os.environ.get("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")).expanduser()
CANONICAL_ROOTS = (PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT)

WORKSPACE_SOURCE_NAME = "workspace-governor dry-run"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def is_relative_to(path: Path, candidate: Path) -> bool:
    try:
        path.relative_to(candidate)
    except ValueError:
        return False
    return True


def parse_declared_path(line: str) -> Path | None:
    normalized = line.replace("`", "").strip()
    match = re.search(r"(~/[^\s,;`]+|/(?!/)[^\s,;`]+|[A-Za-z]:\\[^\s,;`]+)", normalized)
    if not match:
        return None
    candidate = match.group(1).rstrip(".,:;)")
    if candidate.startswith("~/"):
        return Path(candidate).expanduser()
    if candidate.startswith("/"):
        return Path(candidate)
    if re.match(r"^[A-Za-z]:\\", candidate):
        return None
    return None


def default_workspace_path_review(status: str = "not-needed") -> dict[str, Any]:
    return {
        "status": status,
        "source": None,
        "topology_mode": "generic-repo",
        "topology_confidence": "low",
        "topology_evidence": [],
        "proposed_code_root": None,
        "proposed_runtime_root": None,
        "proposed_cloud_home": None,
        "doc_contract_passed": None,
        "rewrite_candidate_count": 0,
        "question_count": 0,
    }


def classify_workspace_topology(
    root: Path,
    declared_paths: list[str],
    findings: list[dict[str, Any]],
    project_doc_exists: bool,
    registry_exists: bool,
    scripts: list[str],
    notebooks: list[str],
    data_dirs: set[str],
) -> tuple[str, str, list[str], bool]:
    evidence: list[str] = []
    score = 0

    if any(is_relative_to(root, candidate) for candidate in CANONICAL_ROOTS):
        score += 3
        evidence.append("repo lives under a canonical research workspace root")
    if is_relative_to(root, LEGACY_ROOT):
        score += 2
        evidence.append("repo lives under the legacy research workspace root")
    if declared_paths:
        score += 3
        evidence.append("project metadata declares absolute or home-relative paths")
    if any((item.get("title") or "").startswith("Declared path missing:") for item in findings):
        score += 2
        evidence.append("project metadata references a missing declared path")
    if project_doc_exists:
        score += 1
        evidence.append("AGENTS.md is present")
    if registry_exists:
        score += 1
        evidence.append("analysis_registry.yaml is present")
    if scripts:
        score += 1
        evidence.append("scripts or tests were discovered")
    if notebooks or data_dirs:
        score += 1
        evidence.append("analysis artifacts such as notebooks or data directories were discovered")

    if score >= 6:
        return "research-layout", "high", evidence, True
    if score >= 3:
        return "research-layout", "medium", evidence, True
    return "generic-repo", "low", evidence, False


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


def add_unique_action(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


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

    if payload.get("questions"):
        findings.append(
            {
                "title": "Workspace topology remains unresolved",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run reported unresolved workspace questions that should be "
                    "answered before specialist review relies on path assumptions."
                ),
            }
        )
        add_unique_action(
            recommended_actions,
            "Review the workspace-governor dry-run questions before running specialist review lanes.",
        )

    if payload.get("doc_contract", {}).get("passed") is False:
        findings.append(
            {
                "title": "Public/private doc contract is incomplete",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run found that the repo does not fully satisfy the "
                    "README plus AGENTS.md documentation split."
                ),
            }
        )
        add_unique_action(
            recommended_actions,
            "Fix the README and AGENTS.md doc contract before relying on published path guidance.",
        )

    if payload.get("rewrite_candidates"):
        findings.append(
            {
                "title": "Stale hard-coded path assumptions detected",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "workspace-governor dry-run found path rewrite candidates that may invalidate "
                    "implementation or methods assumptions."
                ),
            }
        )
        add_unique_action(
            recommended_actions,
            "Review workspace-governor rewrite candidates before interpreting path-sensitive outputs.",
        )
