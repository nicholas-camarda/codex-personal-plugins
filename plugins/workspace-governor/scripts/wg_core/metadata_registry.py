from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .metadata_parse_scalar import load_text

SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_layout",
    "publish_denylist",
}


def read_metadata_texts(repo_root: Path) -> tuple[str, str]:
    return load_text(repo_root / "analysis_registry.yaml"), load_text(repo_root / "AGENTS.md")


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def review_analysis_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
            "message": None,
        }

    keys = top_level_yaml_keys(load_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    message = None
    if unsupported:
        supported_list = ", ".join(sorted(SUPPORTED_ANALYSIS_REGISTRY_KEYS))
        message = (
            "analysis_registry.yaml contains unsupported top-level keys "
            f"({', '.join(unsupported)}). Supported keys are: {supported_list}."
        )
    return {
        "path": str(path),
        "exists": True,
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
        "message": message,
    }
