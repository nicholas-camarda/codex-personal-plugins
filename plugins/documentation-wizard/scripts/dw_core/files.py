from __future__ import annotations

from pathlib import Path

from .files_constants import (
    DOC_SUFFIXES,
    HIDDEN_DOC_SEGMENTS,
    IGNORED_DIRS,
    NON_PUBLIC_SEGMENTS,
    PRIVATE_DOC_SEGMENTS,
)
from .files_public import is_public_doc, public_doc_surfaces, relative
from .files_walk import iter_files

__all__ = [
    "DOC_SUFFIXES",
    "HIDDEN_DOC_SEGMENTS",
    "IGNORED_DIRS",
    "NON_PUBLIC_SEGMENTS",
    "PRIVATE_DOC_SEGMENTS",
    "is_public_doc",
    "iter_files",
    "public_doc_surfaces",
    "read_text",
    "relative",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
