from __future__ import annotations

from .path_token_checks import (
    is_file_like_token,
    looks_like_dotted_identifier,
    looks_like_non_path_token,
    looks_like_template_path,
)
from .path_tokens import PATH_CONTINUATION_CHARS


def should_skip_path_reference(
    *,
    token: str,
    normalized: str,
    text: str,
    start: int,
    end: int,
    explicit_link: bool,
) -> bool:
    next_char = text[end] if end < len(text) else ""
    prev_char = text[start - 1] if start > 0 else ""
    boundary_skip = (
        not explicit_link
        and next_char
        and (next_char.isalnum() or next_char in PATH_CONTINUATION_CHARS)
    ) or (
        not explicit_link
        and prev_char
        and (prev_char.isalnum() or prev_char in {"_", "-"})
    )
    checks = [
        not normalized,
        token.startswith("http"),
        normalized.startswith(("http://", "https://", "mailto:")),
        looks_like_non_path_token(normalized),
        looks_like_dotted_identifier(normalized),
        not is_file_like_token(normalized),
        prev_char in {"<", ">"},
        next_char in {"<", ">"},
        boundary_skip,
        looks_like_template_path(normalized),
    ]
    return any(checks)
