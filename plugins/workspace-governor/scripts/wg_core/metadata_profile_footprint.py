from __future__ import annotations

from pathlib import Path

from .roots import RESEARCH_ROOT, SIDEPROJECTS_ROOT


def existing_cloud_footprints(repo_name: str) -> tuple[Path, Path | None]:
    existing_cloud_side = SIDEPROJECTS_ROOT / repo_name
    existing_cloud_research = RESEARCH_ROOT / repo_name if (RESEARCH_ROOT / repo_name).exists() else None
    return existing_cloud_side, existing_cloud_research


def profile_from_footprints(
    metadata: dict,
    existing_cloud_side: Path,
    existing_cloud_research: Path | None,
) -> tuple[str, str] | None:
    if metadata["project_type"]:
        return metadata["project_type"], "repo metadata"
    if existing_cloud_side.exists() and existing_cloud_research is None:
        return "sideproject", "existing sideprojects footprint"
    if existing_cloud_research is not None and not existing_cloud_side.exists():
        return "research", "existing research footprint"
    return None
