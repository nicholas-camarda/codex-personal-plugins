from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import _host
from .metadata_profile import infer_project_profile
from .roots import PROJECTS_ROOT, RUNTIME_ROOT

RUNTIME_NAME_RE = re.compile(r"(runtime|scratch|tmp|temp|cache|intermediate|work)", re.I)


def classify_candidate(path: Path, classifications: dict[str, dict[str, str]]) -> dict[str, Any]:
    wg = _host.wg()
    name = wg.slugify(path.name)
    canonical_name = wg.canonical_project_name(path.name)
    git = wg.git_status(path)
    profile = infer_project_profile(path, path.name) if path.is_dir() else None
    current_root = wg.immediate_root_label(path)
    record: dict[str, Any] = {
        "source": str(path),
        "name": path.name,
        "slug": name,
        "current_root": current_root,
        "git_repo": git is not None,
        "git": git,
        "action": "keep",
        "reason": "already compliant",
        "destination": None,
        "rewrite_candidates": wg.rewrite_candidates(path, None) if path.is_dir() else [],
    }

    if current_root != "legacy":
        return record

    classification = classifications.get(name)
    destination = None
    reason = None
    if classification:
        destination = wg.suggested_destination(
            path.name,
            {"profile_guess": classification["kind"], "research_domain": classification["domain"]},
            classification,
        )
        reason = f"explicit {classification['kind']} classification"
    elif git is not None:
        destination = PROJECTS_ROOT / canonical_name
        reason = "legacy git repo inferred as general software repo"
    elif RUNTIME_NAME_RE.search(path.name):
        destination = RUNTIME_ROOT / canonical_name
        reason = "legacy runtime/scratch naming"
    elif profile and profile["profile_guess"] in {"research", "sideproject"}:
        destination = wg.suggested_destination(path.name, profile)
        reason = f"repo metadata and heuristics infer {profile['profile_guess']}"

    if destination is None:
        record["action"] = "needs-classification"
        record["reason"] = "ambiguous legacy tree"
        return record

    record["action"] = "move"
    record["reason"] = reason
    record["destination"] = str(destination)
    record["rewrite_candidates"] = wg.rewrite_candidates(path, destination)
    return record
