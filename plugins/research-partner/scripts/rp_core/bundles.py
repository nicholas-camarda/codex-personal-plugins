from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .lanes import write_json

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


def bundle_review(preflight_path: Path, lane_paths: list[Path]) -> dict[str, Any]:
    preflight = load_json(preflight_path)
    lanes = [load_json(path) for path in lane_paths]
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    artifact_map = dict(preflight.get("artifact_map", {}))
    evidence_sources = [str(preflight_path)]
    for lane_path, lane in zip(lane_paths, lanes):
        evidence_sources.append(str(lane_path))
        for key, value in lane.get("artifact_map", {}).items():
            artifact_map.setdefault(key, value)
        for finding in lane.get("findings", []):
            if not isinstance(finding, dict):
                continue
            existing = merged.get(finding_key(finding))
            finding_severity = SEVERITY_ORDER.get(finding.get("severity", "P3"), 3)
            if existing is None or finding_severity < SEVERITY_ORDER.get(
                existing.get("severity", "P3"), 3
            ):
                merged[finding_key(finding)] = finding
    for finding in preflight.get("findings", []):
        if isinstance(finding, dict):
            merged.setdefault(finding_key(finding), finding)

    findings = sorted(
        merged.values(),
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity", "P3"), 3),
            item.get("title") or item.get("message") or "",
        ),
    )
    recommended_actions = []
    for lane in [preflight, *lanes]:
        for action in lane.get("recommended_actions", []):
            if action not in recommended_actions:
                recommended_actions.append(action)

    return {
        "scope": preflight.get("scope", "multi-lane-review"),
        "artifact_map": artifact_map,
        "findings": findings,
        "direct_evidence_vs_inference": (
            "This bundle preserves each lane's evidence basis and deduplicates overlapping "
            "findings by lane and title/message."
        ),
        "required_tests_checks": sorted(
            {check for lane in [preflight, *lanes] for check in lane.get("required_tests_checks", [])}
        ),
        "recommended_actions": recommended_actions,
        "flow": DEFAULT_FLOW,
        "evidence_bundle": evidence_sources,
    }
