from __future__ import annotations

from pathlib import Path
from typing import Any


def verify_git_state(item: dict[str, Any], check: dict[str, Any], wg: Any, failures: list[str]) -> None:
    pre_git = item.get("pre_git")
    dst = Path(item["destination"])
    if pre_git is None or not dst.exists():
        return
    destination_git = wg.git_status(dst)
    check["destination_git"] = destination_git
    head_mismatch = destination_git and destination_git.get("head") != pre_git.get("head")
    porcelain_mismatch = destination_git and destination_git.get("porcelain") != pre_git.get("porcelain")
    if not destination_git or head_mismatch or porcelain_mismatch:
        failures.append(f"Git mismatch after move: {dst}")
