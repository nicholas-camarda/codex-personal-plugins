from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace import parse_declared_path, read_text

DECLARED_PATH_HINTS = (
    "/Users/",
    "/mnt/",
    "C:\\",
    "~/Projects",
    "~/ProjectsRuntime",
    "SideProjects/",
    "Research/",
    "OneDrive",
)


def collect_declared_paths(project_doc: Path, registry: Path) -> list[str]:
    text = read_text(project_doc) + "\n" + read_text(registry)
    return sorted(
        {
            line.strip()
            for line in text.splitlines()
            if parse_declared_path(line) is not None or any(hint in line for hint in DECLARED_PATH_HINTS)
        }
    )


def missing_declared_path_findings(declared_paths: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in declared_paths:
        candidate = parse_declared_path(path)
        if candidate is None:
            continue
        if not candidate.exists():
            findings.append(
                {
                    "title": f"Declared path missing: {candidate}",
                    "severity": "P2",
                    "evidence_basis": "Direct",
                    "message": "A path declared in project metadata does not exist locally.",
                }
            )
    return findings
