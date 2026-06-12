from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace_roots import CANONICAL_ROOTS, LEGACY_ROOT
from .workspace_paths import is_relative_to


def workspace_topology_score(
    root: Path,
    declared_paths: list[str],
    findings: list[dict[str, Any]],
    project_doc_exists: bool,
    registry_exists: bool,
    scripts: list[str],
    notebooks: list[str],
    data_dirs: set[str],
) -> tuple[int, list[str]]:
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
    return score, evidence
