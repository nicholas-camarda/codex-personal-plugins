from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .verification_stage import stage_move


def apply_one(item: dict[str, Any], backup_root: Path, generation: str, wg: Any) -> dict[str, Any]:
    src = Path(item["source"]).expanduser().resolve()
    dst = Path(item["destination"]).expanduser().resolve()
    result: dict[str, Any] = {
        "source": str(src),
        "destination": str(dst),
        "kind": item.get("reason", "move"),
        "status": "pending",
        "rollback_available": True,
    }

    if not src.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Source does not exist: {src}"
        return result
    if dst.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Destination already exists: {dst}"
        return result

    pre_git = wg.git_status(src)
    pre_sig = wg.tree_signature(src, deep=True)
    result["pre_signature"] = pre_sig
    result["pre_git"] = pre_git

    temp_dst = dst.parent / f".{dst.name}.workspace-governor-{generation}"
    result["backup"] = None
    result["temp_destination"] = str(temp_dst)

    try:
        backup, temp_dst, post_state = stage_move(wg, src, dst, backup_root, generation, pre_sig, pre_git)
        result["backup"] = str(backup)
        result.update(post_state)

        try:
            shutil.rmtree(src)
        except Exception as exc:  # noqa: BLE001
            result["status"] = "cleanup-failed"
            result["failure_reason"] = f"Copied to {dst} but could not remove source {src}: {exc}"
            result["source_retained"] = True
            return result

        result["status"] = "moved"
        result["source_retained"] = False
        return result
    except Exception as exc:  # noqa: BLE001
        wg.cleanup_path(temp_dst)
        if dst.exists() and src.exists():
            wg.cleanup_path(dst)
        result["status"] = "failed"
        result["failure_reason"] = str(exc)
        result["source_retained"] = src.exists()
        return result
