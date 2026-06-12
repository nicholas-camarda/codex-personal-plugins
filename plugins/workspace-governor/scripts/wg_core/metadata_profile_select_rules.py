from __future__ import annotations

from .metadata_profile_select_signals import research_profile_match, sideproject_profile_match
from .roots import RESEARCH_ROOT, SIDEPROJECTS_ROOT


def select_profile(
    metadata: dict,
    repo_name: str,
    research_score: int,
    sideproject_score: int,
    research_name_hit: bool,
    sideproject_name_hit: bool,
    research_content_hits: int,
    sideproject_content_hits: int,
    software_signals: list[str],
) -> tuple[str, str]:
    existing_cloud_side = SIDEPROJECTS_ROOT / repo_name
    existing_cloud_research = RESEARCH_ROOT / repo_name if (RESEARCH_ROOT / repo_name).exists() else None

    if metadata["project_type"]:
        return metadata["project_type"], "repo metadata"
    if existing_cloud_side.exists() and existing_cloud_research is None:
        return "sideproject", "existing sideprojects footprint"
    if existing_cloud_research is not None and not existing_cloud_side.exists():
        return "research", "existing research footprint"

    research_domain = metadata["research_domain"]
    if research_profile_match(
        research_score,
        sideproject_score,
        research_domain,
        research_content_hits,
        research_name_hit,
        software_signals,
    ):
        return "research", "research domain signals"
    if sideproject_profile_match(
        research_score,
        sideproject_score,
        sideproject_content_hits,
        sideproject_name_hit,
        software_signals,
    ):
        return "sideproject", "sideproject signals"
    if software_signals:
        return "general", "standard software-repo signals"
    return "general", "weak domain evidence"
