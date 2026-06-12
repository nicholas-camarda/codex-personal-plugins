from __future__ import annotations

from pathlib import Path
from typing import Any

from .bundle_common import SEVERITY_ORDER, finding_key


def merge_lane_findings(
    preflight: dict[str, Any],
    lane_paths: list[Path],
    lanes: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    artifact_map = dict(preflight.get("artifact_map", {}))
    for lane_path, lane in zip(lane_paths, lanes):
        for key, value in lane.get("artifact_map", {}).items():
            artifact_map.setdefault(key, value)
        for finding in lane.get("findings", []):
            if not isinstance(finding, dict):
                continue
            existing = merged.get(finding_key(finding))
            finding_severity = SEVERITY_ORDER.get(finding.get("severity", "P3"), 3)
            if existing is None or finding_severity < SEVERITY_ORDER.get(existing.get("severity", "P3"), 3):
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
    return artifact_map, findings, recommended_actions
