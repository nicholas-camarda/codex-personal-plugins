from __future__ import annotations


def research_profile_match(
    research_score: int,
    sideproject_score: int,
    research_domain: str | None,
    research_content_hits: int,
    research_name_hit: bool,
    software_signals: list[str],
) -> bool:
    if research_score <= sideproject_score:
        return False
    if research_score < 4:
        return False
    if research_domain:
        return True
    if research_content_hits >= 2:
        return True
    return research_name_hit and not software_signals


def sideproject_profile_match(
    research_score: int,
    sideproject_score: int,
    sideproject_content_hits: int,
    sideproject_name_hit: bool,
    software_signals: list[str],
) -> bool:
    if sideproject_score <= research_score:
        return False
    if sideproject_score < 4:
        return False
    if sideproject_content_hits >= 2:
        return True
    return sideproject_name_hit and not software_signals
