from __future__ import annotations

from pathlib import Path
from typing import Any

from .bundle_common import DEFAULT_FLOW, load_json
from .bundle_findings import merge_lane_findings


def bundle_review(preflight_path: Path, lane_paths: list[Path]) -> dict[str, Any]:
    preflight = load_json(preflight_path)
    lanes = [load_json(path) for path in lane_paths]
    artifact_map, findings, recommended_actions = merge_lane_findings(preflight, lane_paths, lanes)
    evidence_sources = [str(preflight_path), *[str(path) for path in lane_paths]]
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
