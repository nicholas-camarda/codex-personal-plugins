from __future__ import annotations

from pathlib import Path
from typing import Any

from .docs_filter_line import load_doc_ref_line, referenced_path_token
from .docs_filter_patterns import NON_PATH_TOKEN_RE, REMOTE_URL_RE


def should_skip_broken_path_finding(repo_root: Path, finding: dict[str, Any]) -> bool:
    doc_ref = finding.get("doc_ref")
    source_line = load_doc_ref_line(repo_root, doc_ref)
    if REMOTE_URL_RE.search(source_line):
        return True
    token = referenced_path_token(finding.get("message"))
    if token and NON_PATH_TOKEN_RE.fullmatch(token):
        return True
    return False
