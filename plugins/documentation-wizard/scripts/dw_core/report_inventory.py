from __future__ import annotations

import re
from pathlib import Path

from .files import read_text
from .interfaces import FLAG_RE, locate_line
from .report_inventory_docs import inventory_docs
from .report_registry import SUPPORTED_ANALYSIS_REGISTRY_KEYS, analysis_registry_review, top_level_yaml_keys

BACKTICK_RE = re.compile(r"`([^`]+)`")


def documented_tokens(root: Path) -> dict[str, dict[str, str]]:
    flags: dict[str, str] = {}
    config_keys: dict[str, str] = {}
    for rel_path in inventory_docs(root)["public_doc_surfaces"]:
        path = root / rel_path
        text = read_text(path)
        for flag in FLAG_RE.findall(text):
            flags.setdefault(flag, f"{rel_path}:{locate_line(path, flag) or 1}")
        for token in BACKTICK_RE.findall(text):
            if "/" in token or token.startswith("--"):
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", token):
                config_keys.setdefault(token, f"{rel_path}:{locate_line(path, token) or 1}")
    return {"flags": flags, "config_keys": config_keys}
