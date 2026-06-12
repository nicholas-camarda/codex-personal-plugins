from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .metadata_parse import load_text, slugify
from .paths_constants import IGNORED_PUBLIC_DOC_PARTS, TEXT_SUFFIXES
from .paths_scan import iter_repo_files
from .roots import LEGACY_ROOT

HOME = Path.home()
PATH_RE = re.compile(r"(?:(?:~|/Users/[^'\"\s]+)|(?:[A-Za-z]:\\[^'\"\s]+)|(?:\.\.?/[^'\"\s]+))")


def rewrite_candidates(repo_root: Path, destination: Path | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in iter_repo_files(repo_root, TEXT_SUFFIXES):
        rel_path = path.relative_to(repo_root)
        rel_parts = {part.lower() for part in rel_path.parts}
        if any(part.startswith(".") for part in rel_path.parts[:-1]):
            continue
        if rel_parts & IGNORED_PUBLIC_DOC_PARTS:
            continue
        text = load_text(path, limit=16000)
        if not text:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            for match in PATH_RE.findall(line):
                normalized = match.strip().strip("'\"`,")
                expanded = normalized.replace("~", str(HOME), 1) if normalized.startswith("~") else normalized
                if "Desktop/coding" not in expanded and str(LEGACY_ROOT) not in expanded:
                    continue
                suggestion = str(destination) if destination and slugify(repo_root.name) in expanded else None
                candidates.append(
                    {
                        "file": str(rel_path),
                        "line": index,
                        "current_path": normalized,
                        "reason": "legacy-absolute-path",
                        "suggested_replacement": suggestion,
                    }
                )
    return candidates
