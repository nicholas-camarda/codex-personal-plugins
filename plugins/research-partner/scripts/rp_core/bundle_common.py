from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

DEFAULT_FLOW = [
    "review-preflight",
    "documentation-wizard",
    "implementation-auditor",
    "stats-reviewer",
    "scientific-reviewer",
    "literature-support-reviewer",
    "robustness-test-designer",
    "review-synthesizer",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def finding_key(finding: dict[str, Any]) -> tuple[Any, ...]:
    return (
        finding.get("lane"),
        finding.get("title") or finding.get("message"),
    )
