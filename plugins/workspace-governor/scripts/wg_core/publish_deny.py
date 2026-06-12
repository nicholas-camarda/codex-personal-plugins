from __future__ import annotations

import fnmatch
import os
from pathlib import Path, PurePosixPath

DEFAULT_PUBLISH_LAYOUT = "mirror-runtime-v1"
GLOBAL_PUBLISH_DENYLIST = [
    ".DS_Store",
    "**/.DS_Store",
    ".env",
    "**/.env",
    "**/.env.*",
    "**/*.log",
    "**/*.tmp",
    "**/*.temp",
    "**/*.cache",
    "**/*.rds",
    "**/*.RData",
    "**/*.Rhistory",
    "**/*.pyc",
    "**/*.pyo",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/logs/**",
    "**/test_output/**",
    "**/tools_output/**",
    "**/tmp/**",
    "**/temp/**",
    "**/cache/**",
    "**/caches/**",
    "**/scratch/**",
    "**/intermediate/**",
    "**/migration_backups/**",
    "**/.git/**",
    "**/*diagnostic*",
    "**/*diagnostics*",
    "**/publish_manifest.json",
]


def relative_to_runtime(path: Path, runtime_root: Path) -> str:
    return path.relative_to(runtime_root).as_posix()


def path_denied(rel_path: str, denylist: list[str]) -> bool:
    normalized = rel_path.replace(os.sep, "/")
    path_obj = PurePosixPath(normalized)
    for pattern in denylist:
        candidate_patterns = [pattern]
        if pattern.startswith("**/"):
            candidate_patterns.append(pattern[3:])
        for candidate in candidate_patterns:
            if fnmatch.fnmatch(normalized, candidate):
                return True
            if path_obj.match(candidate):
                return True
    return False
