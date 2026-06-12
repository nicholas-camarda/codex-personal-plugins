from __future__ import annotations

import os
from pathlib import Path
from typing import Any

IGNORED_WALK_DIRS = {
    ".git",
    ".history",
    ".codex",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "migration_backups",
}


def lane_payload(
    *,
    lane: str,
    root: Path,
    artifact_map: dict[str, Any],
    findings: list[dict[str, Any]],
    required_tests_checks: list[str],
    recommended_actions: list[str],
    direct_evidence_vs_inference: str,
) -> dict[str, Any]:
    return {
        "scope": "research-review-lane",
        "lane": lane,
        "artifact_map": {"repo_root": str(root), **artifact_map},
        "findings": findings,
        "direct_evidence_vs_inference": direct_evidence_vs_inference,
        "required_tests_checks": required_tests_checks,
        "recommended_actions": recommended_actions,
    }


def repo_files(root: Path, suffixes: set[str]) -> list[str]:
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_WALK_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() in suffixes:
                paths.append(path.relative_to(root).as_posix())
    return sorted(paths)
