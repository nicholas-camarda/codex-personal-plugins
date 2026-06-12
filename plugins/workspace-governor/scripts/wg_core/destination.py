from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .metadata import load_text, slugify
from .paths import (
    IGNORED_AUDIT_CHILD_DIRS,
    IGNORED_PUBLIC_DOC_PARTS,
    TEXT_SUFFIXES,
    canonical_project_name,
    iter_repo_files,
)
from .roots import LEGACY_ROOT, PROJECTS_ROOT, RESEARCH_ROOT, RUNTIME_ROOT, SIDEPROJECTS_ROOT

HOME = Path.home()
PATH_RE = re.compile(r"(?:(?:~|/Users/[^'\"\s]+)|(?:[A-Za-z]:\\[^'\"\s]+)|(?:\.\.?/[^'\"\s]+))")


def immediate_root_label(path: Path) -> str:
    resolved = path.expanduser().resolve()
    labeled_roots = [
        ("legacy", LEGACY_ROOT),
        ("runtime", RUNTIME_ROOT),
        ("projects", PROJECTS_ROOT),
        ("research", RESEARCH_ROOT),
        ("sideprojects", SIDEPROJECTS_ROOT),
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
        if classification["kind"] == "research":
            return RESEARCH_ROOT / slug
        return SIDEPROJECTS_ROOT / slug
    if profile["profile_guess"] == "general":
        return None
    if profile["profile_guess"] == "research":
        return RESEARCH_ROOT / slug
    if profile["profile_guess"] == "sideproject":
        return SIDEPROJECTS_ROOT / slug
    return None


def rewrite_candidates(repo_root: Path, destination: Path | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in iter_repo_files(repo_root, TEXT_SUFFIXES):
        rel_path = path.relative_to(repo_root)
        rel_parts = {part.lower() for part in rel_path.parts}
        if any(part.startswith(".") for part in rel_path.parts[:-1]):
            continue
        if rel_parts & IGNORED_PUBLIC_DOC_PARTS:
            continue
        text = load_text(path, limit=16000)
        if not text:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            for match in PATH_RE.findall(line):
                normalized = match.strip().strip("'\"`,")
                expanded = normalized.replace("~", str(HOME), 1) if normalized.startswith("~") else normalized
                if "Desktop/coding" not in expanded and str(LEGACY_ROOT) not in expanded:
                    continue
                suggestion = str(destination) if destination and slugify(repo_root.name) in expanded else None
                candidates.append(
                    {
                        "file": str(rel_path),
                        "line": index,
                        "current_path": normalized,
                        "reason": "legacy-absolute-path",
                        "suggested_replacement": suggestion,
                    }
                )
    return candidates


def build_dry_run_questions(profile: dict[str, Any], destination: Path | None) -> list[str]:
    questions: list[str] = []
    registry_review = profile["metadata"].get("registry_review") or {}
    if registry_review.get("exists") and not registry_review.get("supported", True):
        questions.append(
            "Should analysis_registry.yaml be rewritten to the supported top-level metadata "
            "contract before relying on it?"
        )
    if profile["profile_guess"] == "general":
        questions.append("Should this repo stay in place, or be moved into the managed workspace layout?")
    elif profile["profile_guess"] == "unknown":
        questions.append("Should this repo be treated as Research, SideProjects, or as a general software repo?")
    if profile["has_legacy_paths"]:
        questions.append("Are legacy Desktop/coding paths safe to rewrite after migration?")
    if profile["current_root_kind"] == "legacy" and (
        profile["existing_footprints"].get("runtime")
        or profile["existing_footprints"].get("projects")
        or profile["existing_footprints"].get("sideprojects")
        or profile["existing_footprints"].get("research")
    ):
        questions.append("Which existing local tree is authoritative if there are duplicates?")
    if destination is None:
        if profile["profile_guess"] == "general":
            questions.append("If this repo needs a managed destination, what root should it use?")
        else:
            questions.append("What canonical destination should this project use?")
    questions.append("Which test or smoke command should define migration success?")
    return questions
