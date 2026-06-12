from __future__ import annotations

import os
from pathlib import Path

from .files_constants import HIDDEN_DOC_SEGMENTS, NON_PUBLIC_SEGMENTS


def iter_files(root: Path, suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".")
            and name.lower() not in HIDDEN_DOC_SEGMENTS
            and name.lower() not in NON_PUBLIC_SEGMENTS
        ]
        current = Path(dirpath)
        rel_dir = current.relative_to(root)
        if rel_dir != Path(".") and any(
            part.startswith(".") or part.lower() in NON_PUBLIC_SEGMENTS for part in rel_dir.parts
        ):
            continue
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() not in suffixes:
                continue
            files.append(path)
    return sorted(files)
