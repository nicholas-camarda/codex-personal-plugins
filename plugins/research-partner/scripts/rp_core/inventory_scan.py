from __future__ import annotations

import os
from pathlib import Path

from .lane_runners_common import IGNORED_WALK_DIRS


def scan_repo_artifacts(root: Path) -> tuple[list[str], list[str], set[str]]:
    scripts: list[str] = []
    notebooks: list[str] = []
    data_dirs: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_WALK_DIRS]
        current = Path(dirpath)
        rel_dir = current.relative_to(root)
        if rel_dir != Path(".") and current.name in {"data", "output", "outputs", "results", "reports", "final"}:
            data_dirs.add(rel_dir.as_posix())
        for filename in filenames:
            path = current / filename
            rel_path = path.relative_to(root).as_posix()
            if current.name in {"scripts", "tests"}:
                scripts.append(rel_path)
            if path.suffix.lower() == ".ipynb":
                notebooks.append(rel_path)
    return scripts, notebooks, data_dirs
