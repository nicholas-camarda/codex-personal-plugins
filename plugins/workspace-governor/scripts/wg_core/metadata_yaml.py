from __future__ import annotations

import re


def extract_list(text: str, key: str) -> list[str]:
    inline = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$", text)
    if inline:
        values = []
        for item in inline.group(1).split(","):
            normalized = item.strip().strip("'\"`")
            if normalized:
                values.append(normalized)
        return values

    lines = text.splitlines()
    values: list[str] = []
    active = False
    base_indent = 0
    key_pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*$")
    for line in lines:
        if not active:
            match = key_pattern.match(line)
            if not match:
                continue
            active = True
            base_indent = len(match.group(1))
            continue
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip(" "))
        if not stripped:
            continue
        if current_indent <= base_indent and not stripped.startswith("- "):
            break
        bullet_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if bullet_match:
            values.append(bullet_match.group(1).strip().strip("'\"`"))
            continue
        break
    return values
