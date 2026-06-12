from __future__ import annotations

from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload


def literature_support_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    registry_path = preflight.get("artifact_map", {}).get("analysis_registry")
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if registry_path is None:
        findings.append(
            {
                "title": "Literature support context is under-specified",
                "severity": "P3",
                "evidence_basis": "Missing",
                "message": (
                    "No analysis_registry.yaml was discovered, so domain and method context for "
                    "literature support is incomplete."
                ),
                "lane": "literature-support-reviewer",
            }
        )
        actions.append(
            "Add or update analysis_registry.yaml with project type, domain, and analysis context "
            "before literature support review."
        )
    return lane_payload(
        lane="literature-support-reviewer",
        root=root,
        artifact_map={"analysis_registry": registry_path},
        findings=findings,
        required_tests_checks=[
            "Tie any literature citation to the actual design, population, endpoint, and implementation details.",
        ],
        recommended_actions=actions,
        direct_evidence_vs_inference=(
            "This lane checks whether enough local context exists for a literature support review; "
            "it does not perform external literature search."
        ),
    )
