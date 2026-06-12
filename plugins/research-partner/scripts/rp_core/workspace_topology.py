from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace_paths import is_relative_to
from .workspace_topology_score import workspace_topology_score


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
    score, evidence = workspace_topology_score(
        root,
        declared_paths,
        findings,
        project_doc_exists,
        registry_exists,
        scripts,
        notebooks,
        data_dirs,
    )
    if score >= 6:
        return "research-layout", "high", evidence, True
    if score >= 3:
        return "research-layout", "medium", evidence, True
    return "generic-repo", "low", evidence, False
