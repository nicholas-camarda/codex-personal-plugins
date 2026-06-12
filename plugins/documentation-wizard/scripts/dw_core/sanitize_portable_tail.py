from __future__ import annotations


def portable_tail(path_text: str, min_parts: int = 2) -> str | None:
    trailing_slash = path_text.endswith("/")
    trimmed = path_text.rstrip("/")
    if not trimmed:
        return None
    parts = [part for part in trimmed.split("/") if part and part != "~"]
    if not parts:
        return None
    count = min(len(parts), max(1, min_parts))
    tail = "/".join(parts[-count:])
    if trailing_slash:
        return f"{tail}/"
    return tail
