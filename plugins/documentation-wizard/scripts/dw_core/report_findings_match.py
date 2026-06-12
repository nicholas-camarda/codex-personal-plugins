from __future__ import annotations

import difflib


def closest_match(token: str, candidates: list[str]) -> str | None:
    matches = difflib.get_close_matches(token, candidates, n=1, cutoff=0.5)
    return matches[0] if matches else None
