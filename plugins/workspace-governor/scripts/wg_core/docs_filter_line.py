from __future__ import annotations

import re
from pathlib import Path

REFERENCED_PATH_RE = re.compile(r"Referenced path `([^`]+)`")


def parse_doc_ref_path(doc_ref: str | None) -> str | None:
    if not doc_ref:
        return None
    return doc_ref.split(":", 1)[0]


def load_doc_ref_line(repo_root: Path, doc_ref: str | None) -> str:
    if not doc_ref or ":" not in doc_ref:
        return ""
    doc_path, line_text = doc_ref.rsplit(":", 1)
    if not line_text.isdigit():
        return ""
    path = repo_root / doc_path
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    line_number = int(line_text)
    if line_number < 1 or line_number > len(lines):
        return ""
    return lines[line_number - 1]


def referenced_path_token(message: str | None) -> str | None:
    if not message:
        return None
    match = REFERENCED_PATH_RE.search(message)
    if not match:
        return None
    return match.group(1)
