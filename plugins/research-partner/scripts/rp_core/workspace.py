from __future__ import annotations

import re
from pathlib import Path

from .workspace_handoff import add_unique_action, append_workspace_findings, run_workspace_governor_dry_run
from .workspace_paths import is_relative_to
from .workspace_topology import classify_workspace_topology, default_workspace_path_review

__all__ = [
    "add_unique_action",
    "append_workspace_findings",
    "classify_workspace_topology",
    "default_workspace_path_review",
    "is_relative_to",
    "parse_declared_path",
    "read_text",
    "run_workspace_governor_dry_run",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def parse_declared_path(line: str) -> Path | None:
    normalized = line.replace("`", "").strip()
    match = re.search(r"(~/[^\s,;`]+|/(?!/)[^\s,;`]+|[A-Za-z]:\\[^\s,;`]+)", normalized)
    if not match:
        return None
    candidate = match.group(1).rstrip(".,:;)")
    if candidate.startswith("~/"):
        return Path(candidate).expanduser()
    if candidate.startswith("/"):
        return Path(candidate)
    if re.match(r"^[A-Za-z]:\\", candidate):
        return None
    return None
