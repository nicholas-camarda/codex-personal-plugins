from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli_flags import locate_line
from .files import public_doc_surfaces, read_text
from .path_token_checks import looks_like_generated_output_path
from .path_token_skip import should_skip_path_reference
from .path_tokens import (
    MARKDOWN_LINK_RE,
    PATH_TOKEN_RE,
    is_valid_relative_doc_link,
    normalize_path_token,
    referenced_path_exists,
)


def collect_referenced_paths(root: Path) -> list[dict[str, Any]]:
    referenced_paths: list[dict[str, Any]] = []
    for path in public_doc_surfaces(root):
        doc_path = root / path
        text = read_text(doc_path)
        candidates: list[tuple[str, int, int, bool]] = []
        candidates.extend(
            (match.group(1), match.start(1), match.end(1), True) for match in MARKDOWN_LINK_RE.finditer(text)
        )
        candidates.extend(
            (match.group(0), match.start(0), match.end(0), False) for match in PATH_TOKEN_RE.finditer(text)
        )
        seen_tokens: set[str] = set()
        for token, start, end, explicit_link in candidates:
            normalized = normalize_path_token(token)
            if normalized in seen_tokens:
                continue
            seen_tokens.add(normalized)
            if should_skip_path_reference(
                token=token,
                normalized=normalized,
                text=text,
                start=start,
                end=end,
                explicit_link=explicit_link,
            ):
                continue
            if is_valid_relative_doc_link(root, path, normalized):
                continue
            if looks_like_generated_output_path(normalized):
                continue
            referenced_paths.append(
                {
                    "path": normalized,
                    "doc_ref": f"{path}:{locate_line(doc_path, token) or 1}",
                    "exists": referenced_path_exists(root, path, normalized),
                }
            )
    return referenced_paths
