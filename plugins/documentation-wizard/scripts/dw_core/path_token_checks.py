from __future__ import annotations

from pathlib import Path

from .path_tokens import (
    ABBREVIATION_LIKE_RE,
    DOMAIN_LIKE_RE,
    FILE_LIKE_SUFFIXES,
    GENERATED_OUTPUT_ROOT_SEGMENTS,
    VERSION_LIKE_RE,
    _FILE_SUFFIXES_LOWER,
    normalize_path_token,
)


def looks_like_non_path_token(token: str) -> bool:
    normalized = token.strip()
    checks = [
        not normalized,
        normalized.startswith("//"),
        bool(VERSION_LIKE_RE.fullmatch(normalized)),
        bool(DOMAIN_LIKE_RE.fullmatch(normalized)),
    ]
    return any(checks)


def looks_like_dotted_identifier(token: str) -> bool:
    normalized = token.rstrip(".,:;)")
    if "/" in normalized or normalized.startswith(("~", "/", "./", "../")):
        return False
    if ABBREVIATION_LIKE_RE.fullmatch(normalized):
        return True
    if "." not in normalized:
        return False
    suffix = Path(normalized).suffix
    return suffix.lower() not in _FILE_SUFFIXES_LOWER


def looks_like_template_path(token: str) -> bool:
    return any(marker in token for marker in ("<", ">", "{", "}"))


def is_file_like_token(token: str) -> bool:
    normalized = token.rstrip(".,:;)")
    if "/" in normalized:
        if normalized.startswith("/") and normalized.count("/") == 1:
            suffix = Path(normalized).suffix
            return suffix.lower() in _FILE_SUFFIXES_LOWER
        return True
    suffix = Path(normalized).suffix
    return suffix.lower() in _FILE_SUFFIXES_LOWER


def looks_like_generated_output_path(token: str) -> bool:
    normalized = normalize_path_token(token)
    if normalized.startswith(("~", "/", "./", "../")):
        return False
    parts = Path(normalized).parts
    return bool(parts) and parts[0].lower() in GENERATED_OUTPUT_ROOT_SEGMENTS
