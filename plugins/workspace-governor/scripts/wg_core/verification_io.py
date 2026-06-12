from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def copytree_verified(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True, copy_function=shutil.copy2)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
