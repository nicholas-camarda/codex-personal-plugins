from __future__ import annotations

import os
from pathlib import Path


DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
PRIVATE_DOC_SEGMENTS = {"internal", "private"}
HIDDEN_DOC_SEGMENTS = {".git", ".history", ".codex"}
NON_PUBLIC_SEGMENTS = {
    "archive",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "migration_backups",
}
IGNORED_DIRS = HIDDEN_DOC_SEGMENTS | NON_PUBLIC_SEGMENTS


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


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


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_public_doc(rel_path: str) -> bool:
    rel = Path(rel_path)
    name = rel.name.lower()
    if ".local." in name:
        return False
    if any(part.startswith(".") for part in rel.parts[:-1]):
        return False
    if any(part.lower() in HIDDEN_DOC_SEGMENTS for part in rel.parts):
        return False
    if any(part.lower() in NON_PUBLIC_SEGMENTS for part in rel.parts):
        return False
    if any(part.lower() in PRIVATE_DOC_SEGMENTS for part in rel.parts):
        return False
    return True


def public_doc_surfaces(root: Path) -> list[str]:
    doc_surfaces = []
    for path in iter_files(root, DOC_SUFFIXES):
        rel = relative(path, root)
        if rel.startswith("docs/") or path.name.upper().startswith(("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")):
            doc_surfaces.append(rel)
    return [rel for rel in doc_surfaces if is_public_doc(rel)]
