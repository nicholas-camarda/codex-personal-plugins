from __future__ import annotations

from pathlib import Path
from typing import Any

from .destination_questions import build_dry_run_questions
from .destination_rewrite import rewrite_candidates
from .paths import IGNORED_AUDIT_CHILD_DIRS, canonical_project_name
from .roots import (
    LEGACY_ROOT,
    PROJECT_VAULT_ROOT,
    PROJECTS_ROOT,
    RESEARCH_ROOT,
    RESIDENCY_ROOT,
    RUNTIME_ROOT,
    SIDEPROJECTS_ROOT,
    WORKSPACES_ROOT,
)


def immediate_root_label(path: Path) -> str:
    resolved = path.expanduser().resolve()
    labeled_roots = [
        ("legacy", LEGACY_ROOT),
        ("runtime", RUNTIME_ROOT),
        ("projects", PROJECTS_ROOT),
        ("research", RESEARCH_ROOT),
        ("sideprojects", SIDEPROJECTS_ROOT),
        ("workspace", WORKSPACES_ROOT),
        ("project-vault", PROJECT_VAULT_ROOT),
        ("residency", RESIDENCY_ROOT),
    ]
    for label, root in labeled_roots:
        try:
            resolved.relative_to(root.expanduser().resolve())
            return label
        except ValueError:
            continue
    return "other"


def child_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".") and path.name.lower() not in IGNORED_AUDIT_CHILD_DIRS
        ],
        key=lambda p: p.name.lower(),
    )


def suggested_destination(
    repo_name: str,
    profile: dict[str, Any],
    classification: dict[str, str] | None = None,
) -> Path | None:
    slug = canonical_project_name(repo_name)
    if classification:
        return WORKSPACES_ROOT / slug
    if profile["profile_guess"] == "general":
        return None
    return WORKSPACES_ROOT / slug


__all__ = [
    "build_dry_run_questions",
    "child_dirs",
    "immediate_root_label",
    "rewrite_candidates",
    "suggested_destination",
]
