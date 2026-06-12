from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .files import public_doc_surfaces, read_text


DATE_SEGMENT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILE_LIKE_SUFFIXES = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".adoc",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".pdf",
    ".py",
    ".R",
    ".r",
    ".qmd",
    ".ipynb",
    ".ts",
    ".js",
}
GENERATED_OUTPUT_ROOT_SEGMENTS = {
    "artifacts",
    "dashboard",
    "diagnostics",
    "figures",
    "logs",
    "output",
    "outputs",
    "plots",
    "results",
    "run",
    "runs",
}


@dataclass(frozen=True)
class InfraPattern:
    regex: re.Pattern[str]
    fallback: str


PRIVATE_INFRA_PATTERNS = [
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:Library/CloudStorage/OneDrive(?:-Personal| - Personal)?)/[^\s`]+"),
        "the configured synced project home",
    ),
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:ProjectsRuntime)(?:/[^\s`]+)?"),
        "the configured runtime output directory",
    ),
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:Projects)(?:/[^\s`]+)?"),
        "the local source checkout",
    ),
    InfraPattern(
        re.compile(r"/Users/[^\s`]+"),
        "the configured local path",
    ),
    InfraPattern(
        re.compile(r"OneDrive(?:-Personal| - Personal)?"),
        "the synced project home",
    ),
]


def _portable_tail(path_text: str, min_parts: int = 2) -> str | None:
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
        if (
            segment.lower() in GENERATED_OUTPUT_ROOT_SEGMENTS
            or DATE_SEGMENT_RE.fullmatch(segment)
            or Path(segment).suffix.lower() in {item.lower() for item in FILE_LIKE_SUFFIXES}
        ):
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

    generic_tail = _portable_tail(path_text, min_parts=2)
    return generic_tail or fallback


def replacement_for_match(match: re.Match[str], pattern: InfraPattern) -> str:
    return portable_public_replacement(match.group(0), pattern.fallback)


def find_private_infra_leaks(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rel_path in public_doc_surfaces(root):
        path = root / rel_path
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            line_matches: list[tuple[int, int, str, str]] = []
            for pattern in PRIVATE_INFRA_PATTERNS:
                for match in pattern.regex.finditer(line):
                    replacement = replacement_for_match(match, pattern)
                    line_matches.append((match.start(), match.end(), match.group(0), replacement))
            line_matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
            accepted: list[tuple[int, int, str, str]] = []
            for candidate in line_matches:
                start, end, _, _ = candidate
                if any(start >= kept_start and end <= kept_end for kept_start, kept_end, _, _ in accepted):
                    continue
                accepted.append(candidate)
            for _, _, matched_text, replacement in accepted:
                findings.append(
                    {
                        "kind": "private-infra-leak",
                        "severity": "P1",
                        "evidence_basis": "Direct",
                        "doc_ref": f"{rel_path}:{line_number}",
                        "source_ref": "public-doc-policy",
                        "message": f"Public doc exposes maintainer-specific infrastructure detail `{matched_text}`.",
                        "impact": "Collaborators see maintainer-only storage topology instead of portable setup guidance.",
                        "patch_direction": f"Replace `{matched_text}` with `{replacement}` in {rel_path} and keep the concrete path in AGENTS.md or internal docs.",
                        "replacement": replacement,
                    }
                )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (finding["doc_ref"], finding["message"])
        unique.setdefault(key, finding)
    return list(unique.values())


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
