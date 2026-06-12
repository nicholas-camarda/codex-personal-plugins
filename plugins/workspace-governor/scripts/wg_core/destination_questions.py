from __future__ import annotations

from pathlib import Path
from typing import Any

from .destination_questions_profile import footprint_questions, profile_questions


def build_dry_run_questions(profile: dict[str, Any], destination: Path | None) -> list[str]:
    questions = profile_questions(profile)
    questions.extend(footprint_questions(profile))
    if destination is None:
        if profile["profile_guess"] == "general":
            questions.append("If this repo needs a managed destination, what root should it use?")
        else:
            questions.append("What canonical destination should this project use?")
    questions.append("Which test or smoke command should define migration success?")
    return questions
