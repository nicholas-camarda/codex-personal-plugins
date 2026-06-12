from __future__ import annotations

import os
from pathlib import Path

from .paths_constants import IGNORED_AUDIT_CHILD_DIRS


def iter_repo_files(repo_root: Path, suffixes: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and name.lower() not in IGNORED_AUDIT_CHILD_DIRS
        ]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if suffixes is not None and path.suffix.lower() not in suffixes:
                continue
            files.append(path)
    return sorted(files)
