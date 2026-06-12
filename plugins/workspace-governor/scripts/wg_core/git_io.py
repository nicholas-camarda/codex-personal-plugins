from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def run_git(path: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return proc.stdout.strip()


def git_status(path: Path) -> dict[str, Any] | None:
    top = run_git(path, "rev-parse", "--show-toplevel")
    if not top:
        return None
    porcelain = run_git(path, "status", "--porcelain") or ""
    return {
        "top_level": top,
        "head": run_git(path, "rev-parse", "HEAD"),
        "branch": run_git(path, "branch", "--show-current"),
        "porcelain": porcelain.splitlines(),
        "clean": porcelain == "",
    }


def tree_signature(root: Path, deep: bool = False) -> dict[str, Any]:
    files = []
    dirs = 0
    total_bytes = 0
    digest = hashlib.sha256()

    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if ".git" in path.parts:
            continue
        if path.is_dir():
            dirs += 1
            continue
        if path.is_symlink():
            marker = f"L|{rel}|{os.readlink(path)}"
            digest.update(marker.encode("utf-8"))
            files.append(marker)
            continue
        stat = path.stat()
        total_bytes += stat.st_size
        if deep:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            marker = f"F|{rel}|{stat.st_size}|{stat.st_mode:o}|{file_hash}"
        else:
            marker = f"F|{rel}|{stat.st_size}|{stat.st_mode:o}|{int(stat.st_mtime_ns)}"
        digest.update(marker.encode("utf-8"))
        files.append(marker)
    return {
        "root": str(root),
        "file_count": len(files),
        "dir_count": dirs,
        "total_bytes": total_bytes,
        "digest": digest.hexdigest(),
    }


def signatures_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("file_count", "dir_count", "total_bytes", "digest")
    return all(left.get(key) == right.get(key) for key in keys)


def cleanup_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
