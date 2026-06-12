from __future__ import annotations

from pathlib import Path
from typing import Any

from .files import public_doc_surfaces, read_text
from .sanitize_patterns import PRIVATE_INFRA_PATTERNS
from .sanitize_replace import replacement_for_match


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
                        "impact": (
                            "Collaborators see maintainer-only storage topology instead of "
                            "portable setup guidance."
                        ),
                        "patch_direction": (
                            f"Replace `{matched_text}` with `{replacement}` in {rel_path} "
                            "and keep the concrete path in AGENTS.md or internal docs."
                        ),
                        "replacement": replacement,
                    }
                )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (finding["doc_ref"], finding["message"])
        unique.setdefault(key, finding)
    return list(unique.values())
