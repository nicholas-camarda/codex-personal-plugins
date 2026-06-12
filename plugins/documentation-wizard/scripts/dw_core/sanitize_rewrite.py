from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .files import public_doc_surfaces, read_text
from .sanitize_patterns import PRIVATE_INFRA_PATTERNS
from .sanitize_replace import replacement_for_match


def sanitize_public_docs(root: Path, write: bool = False) -> dict[str, Any]:
    rewrites: list[dict[str, Any]] = []
    changed_files = 0
    for rel_path in public_doc_surfaces(root):
        path = root / rel_path
        original_text = read_text(path)
        updated_text = original_text
        replacements: list[dict[str, Any]] = []
        for pattern in PRIVATE_INFRA_PATTERNS:

            def record_replacement(match: re.Match[str]) -> str:
                replacement = replacement_for_match(match, pattern)
                replacements.append(
                    {
                        "matched": match.group(0),
                        "replacement": replacement,
                    }
                )
                return replacement

            updated_text = pattern.regex.sub(record_replacement, updated_text)
        if updated_text == original_text:
            continue
        changed_files += 1
        rewrites.append(
            {
                "path": rel_path,
                "changed": True,
                "write": bool(write),
                "replacements": replacements,
            }
        )
        if write:
            path.write_text(updated_text, encoding="utf-8")
    return {
        "repo_root": str(root),
        "write": bool(write),
        "changed_files": changed_files,
        "rewrites": rewrites,
    }
