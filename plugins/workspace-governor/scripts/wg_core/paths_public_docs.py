from __future__ import annotations

from pathlib import Path

from .paths_constants import IGNORED_PUBLIC_DOC_PARTS, TEXT_SUFFIXES
from .paths_scan import iter_repo_files


def is_public_doc_path(repo_root: Path, path: Path) -> bool:
    rel_path = path.relative_to(repo_root)
    rel_parts = {part.lower() for part in rel_path.parts}
    if any(part.startswith(".") for part in rel_path.parts[:-1]):
        return False
    if rel_parts & IGNORED_PUBLIC_DOC_PARTS:
        return False
    name = path.name.lower()
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    rel = rel_path.as_posix()
    if rel == "AGENTS.md":
        return False
    if ".local." in name:
        return False
    if any(part.lower() in {"internal", "private"} for part in rel_path.parts):
        return False
    return rel.startswith("docs/") or path.name.upper().startswith(
        ("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")
    )


def public_doc_paths(repo_root: Path) -> list[Path]:
    return [path for path in iter_repo_files(repo_root, TEXT_SUFFIXES) if is_public_doc_path(repo_root, path)]
