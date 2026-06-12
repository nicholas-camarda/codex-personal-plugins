from __future__ import annotations

from typing import Any


def profile_questions(profile: dict[str, Any]) -> list[str]:
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
    return questions


def footprint_questions(profile: dict[str, Any]) -> list[str]:
    if profile["current_root_kind"] != "legacy":
        return []
    footprints = profile["existing_footprints"]
    if not (
        footprints.get("runtime")
        or footprints.get("projects")
        or footprints.get("sideprojects")
        or footprints.get("research")
    ):
        return []
    return ["Which existing local tree is authoritative if there are duplicates?"]
