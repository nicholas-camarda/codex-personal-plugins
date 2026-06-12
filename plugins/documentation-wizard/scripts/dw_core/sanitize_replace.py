from __future__ import annotations

import re
from pathlib import Path

from .sanitize_patterns import (
    DATE_SEGMENT_RE,
    FILE_LIKE_SUFFIXES,
    GENERATED_OUTPUT_ROOT_SEGMENTS,
    InfraPattern,
)
from .sanitize_portable_tail import portable_tail


def portable_suffix_after(path_text: str, marker: str, marker_fallback: str) -> str | None:
    trailing_slash = path_text.endswith("/")
    parts = [part for part in path_text.rstrip("/").split("/") if part and part != "~"]
    if marker not in parts:
        return None
    marker_index = parts.index(marker)
    suffix_parts = parts[marker_index + 2 :]
    if not suffix_parts:
        return marker_fallback
    if len(suffix_parts) == 1:
        segment = suffix_parts[0]
        segment_checks = [
            segment.lower() in GENERATED_OUTPUT_ROOT_SEGMENTS,
            bool(DATE_SEGMENT_RE.fullmatch(segment)),
            Path(segment).suffix.lower() in {item.lower() for item in FILE_LIKE_SUFFIXES},
        ]
        if any(segment_checks):
            tail = "/".join(suffix_parts)
            return f"{tail}/" if trailing_slash else tail
        return marker_fallback
    tail = "/".join(suffix_parts[-2:])
    return f"{tail}/" if trailing_slash else tail


def portable_public_replacement(path_text: str, fallback: str) -> str:
    for marker, marker_fallback in [
        ("ProjectsRuntime", "the configured runtime output directory"),
        ("Projects", "the local source checkout"),
        ("SideProjects", "the configured synced project home"),
        ("Research", "the configured synced project home"),
    ]:
        replacement = portable_suffix_after(path_text, marker, marker_fallback)
        if replacement is not None:
            return replacement

    generic_tail = portable_tail(path_text, min_parts=2)
    return generic_tail or fallback


def replacement_for_match(match: re.Match[str], pattern: InfraPattern) -> str:
    return portable_public_replacement(match.group(0), pattern.fallback)
