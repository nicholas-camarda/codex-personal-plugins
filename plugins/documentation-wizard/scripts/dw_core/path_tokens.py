from __future__ import annotations

import re
from pathlib import Path

from .files import DOC_SUFFIXES


PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?:~?/|/|\./|\../)?[A-Za-z0-9_./<>{}-]+(?:\.[A-Za-z0-9_./<>{}-]+)+"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
DOMAIN_LIKE_RE = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/?$")
VERSION_LIKE_RE = re.compile(r"^\d+(?:\.\d+)+$")
ABBREVIATION_LIKE_RE = re.compile(r"^(?:[A-Z]\.)+[A-Z]?$")
PATH_CONTINUATION_CHARS = set("_-<>{}()[]")
FILE_LIKE_SUFFIXES = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".adoc",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".pdf",
    ".py",
    ".R",
    ".r",
    ".qmd",
    ".ipynb",
    ".ts",
    ".js",
}
GENERATED_OUTPUT_ROOT_SEGMENTS = {
    "artifacts",
    "dashboard",
    "diagnostics",
    "figures",
    "logs",
    "output",
    "outputs",
    "plots",
    "results",
    "run",
    "runs",
}
_FILE_SUFFIXES_LOWER = {item.lower() for item in FILE_LIKE_SUFFIXES}
_DOC_SUFFIXES_LOWER = {item.lower() for item in DOC_SUFFIXES}


def normalize_path_token(token: str) -> str:
    normalized = token.strip().rstrip(".,:;)")
    normalized = normalized.split("#", 1)[0]
    normalized = normalized.split("?", 1)[0]
    return normalized


def referenced_path_exists(root: Path, doc_rel_path: str, token: str) -> bool:
    normalized = normalize_path_token(token)
    if normalized.startswith("~"):
        return Path(normalized).expanduser().exists()
    if normalized.startswith("/"):
        return Path(normalized).exists()
    doc_parent = (root / doc_rel_path).parent
    candidates = [(doc_parent / normalized).resolve()]
    if not normalized.startswith(("./", "../")):
        candidates.append((root / normalized).resolve())
    return any(candidate.exists() for candidate in candidates)


def is_valid_relative_doc_link(root: Path, doc_rel_path: str, token: str) -> bool:
    normalized = normalize_path_token(token)
    suffix = Path(normalized).suffix.lower()
    if suffix not in _DOC_SUFFIXES_LOWER:
        return False
    doc_parent = (root / doc_rel_path).parent
    candidates = [(doc_parent / normalized).resolve()]
    if not normalized.startswith(("./", "../")):
        candidates.append((root / normalized).resolve())
    return any(candidate.exists() for candidate in candidates)
