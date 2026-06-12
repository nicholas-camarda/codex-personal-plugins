from __future__ import annotations


def profile_confidence(
    profile: str,
    metadata: dict,
    research_score: int,
    sideproject_score: int,
    software_signals: list[str],
) -> float:
    confidence = 0.18 + min(0.62, abs(research_score - sideproject_score) / 12)
    if profile == "general":
        confidence = 0.35 if software_signals else 0.25
    if metadata["project_type"]:
        confidence = max(confidence, 0.9)
    if metadata["research_domain"]:
        confidence = max(confidence, 0.92)
    return round(min(confidence, 0.99), 2)
