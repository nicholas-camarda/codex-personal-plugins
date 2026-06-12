from __future__ import annotations

from pathlib import Path

from .files_constants import DOC_SUFFIXES, HIDDEN_DOC_SEGMENTS, NON_PUBLIC_SEGMENTS, PRIVATE_DOC_SEGMENTS
from .files_walk import iter_files


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_public_doc(rel_path: str) -> bool:
    rel = Path(rel_path)
    name = rel.name.lower()
    checks = [
        ".local." in name,
        any(part.startswith(".") for part in rel.parts[:-1]),
        any(part.lower() in HIDDEN_DOC_SEGMENTS for part in rel.parts),
        any(part.lower() in NON_PUBLIC_SEGMENTS for part in rel.parts),
        any(part.lower() in PRIVATE_DOC_SEGMENTS for part in rel.parts),
    ]
    return not any(checks)


def public_doc_surfaces(root: Path) -> list[str]:
    doc_surfaces = []
    for path in iter_files(root, DOC_SUFFIXES):
        rel = relative(path, root)
        if rel.startswith("docs/") or path.name.upper().startswith(("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")):
            doc_surfaces.append(rel)
    return [rel for rel in doc_surfaces if is_public_doc(rel)]
