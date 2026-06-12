from __future__ import annotations

from pathlib import Path


def is_relative_to(path: Path, candidate: Path) -> bool:
    try:
        path.relative_to(candidate)
    except ValueError:
        return False
    return True
