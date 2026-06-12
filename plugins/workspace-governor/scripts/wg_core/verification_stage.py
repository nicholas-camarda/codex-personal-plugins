from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from .verification_io import copytree_verified


def stage_move(
    wg: Any,
    src: Path,
    dst: Path,
    backup_root: Path,
    generation: str,
    pre_sig: dict[str, Any],
    pre_git: dict[str, Any] | None,
) -> tuple[Path, Path, dict[str, Any]]:
    backup = backup_root / re.sub(r"[^A-Za-z0-9._-]+", "_", str(src).lstrip(os.sep))
    temp_dst = dst.parent / f".{dst.name}.workspace-governor-{generation}"
    if backup.exists():
        raise FileExistsError(f"Backup path already exists: {backup}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    copytree_verified(src, backup)

    if temp_dst.exists():
        raise FileExistsError(f"Temporary destination already exists: {temp_dst}")
    temp_dst.parent.mkdir(parents=True, exist_ok=True)
    copytree_verified(src, temp_dst)
    if not wg.signatures_match(wg.tree_signature(temp_dst, deep=True), pre_sig):
        raise RuntimeError(f"Verification failed while staging {src} -> {temp_dst}")
    wg.verify_git_copy(temp_dst, pre_git)

    temp_dst.rename(dst)
    post_sig = wg.tree_signature(dst, deep=True)
    wg.verify_git_copy(dst, pre_git)
    if not wg.signatures_match(post_sig, pre_sig):
        raise RuntimeError(f"Post-move verification failed for {dst}")

    return backup, temp_dst, {
        "post_signature": post_sig,
        "post_git": wg.git_status(dst),
    }
