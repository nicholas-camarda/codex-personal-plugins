from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _host


def resolve_code_plan(
    repo_root: Path,
    profile: dict[str, Any],
    classification: dict[str, str] | None,
) -> tuple[Path | None, Path | None, str | None, bool]:
    wg = _host.wg()
    source_home, source_home_source = wg.configured_source_home(repo_root)
    managed = profile["profile_guess"] != "general"
    already_canonical = managed and repo_root.resolve() == source_home.resolve()
    destination = None if already_canonical else wg.suggested_destination(
        repo_root.name, profile, classification
    )
    if destination is not None:
        destination = source_home
    code_root = source_home if managed else None
    code_root_source = source_home_source if managed else None
    return destination, code_root, code_root_source, already_canonical
