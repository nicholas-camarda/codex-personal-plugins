from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .files import read_text

SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_denylist",
}


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def analysis_registry_review(root: Path) -> dict[str, Any]:
    path = root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "exists": False,
            "path": "analysis_registry.yaml",
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
        }
    keys = top_level_yaml_keys(read_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    return {
        "exists": True,
        "path": "analysis_registry.yaml",
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
    }
