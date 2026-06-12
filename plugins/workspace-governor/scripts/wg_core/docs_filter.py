from __future__ import annotations

from pathlib import Path
from typing import Any

from .docs_filter_findings import should_skip_broken_path_finding
from .docs_filter_line import parse_doc_ref_path


def filter_doc_findings(repo_root: Path, findings: list[dict[str, Any]], public_docs: set[str]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        doc_ref = finding.get("doc_ref")
        doc_path = parse_doc_ref_path(doc_ref)
        if doc_path is None:
            continue
        if doc_path not in public_docs:
            continue
        if finding.get("kind") == "broken-referenced-path":
            if should_skip_broken_path_finding(repo_root, finding):
                continue
        marker = (finding.get("kind"), doc_ref, finding.get("message"))
        if marker in seen:
            continue
        seen.add(marker)
        filtered.append(finding)
    return filtered


def filter_sanitize_preview(sanitize_preview: dict[str, Any], public_docs: set[str]) -> dict[str, Any]:
    if not isinstance(sanitize_preview, dict):
        return {"changed_files": 0, "rewrites": [], "write": False}
    rewrites = [
        rewrite
        for rewrite in sanitize_preview.get("rewrites", [])
        if isinstance(rewrite, dict) and (rewrite.get("file") or rewrite.get("path")) in public_docs
    ]
    filtered = dict(sanitize_preview)
    filtered["rewrites"] = rewrites
    filtered["changed_files"] = sum(1 for rewrite in rewrites if rewrite.get("changed", True))
    return filtered
