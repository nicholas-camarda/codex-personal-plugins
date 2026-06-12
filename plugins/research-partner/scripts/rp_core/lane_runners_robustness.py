from __future__ import annotations

from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload


def robustness_test_designer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    scripts = list(preflight.get("artifact_map", {}).get("scripts_and_tests", []))
    findings: list[dict[str, Any]] = []
    actions = [
        (
            "Add regression tests for artifact presence, schema stability, documented path assumptions, "
            "and one representative analysis smoke run."
        )
    ]
    if scripts:
        findings.append(
            {
                "title": "Robustness test targets identified",
                "severity": "P3",
                "evidence_basis": "Direct",
                "message": (
                    "Executable files were found and should be covered by smoke or regression tests "
                    "tied to scientific failure modes."
                ),
                "lane": "robustness-test-designer",
            }
        )
    return lane_payload(
        lane="robustness-test-designer",
        root=root,
        artifact_map={"scripts_and_tests": scripts},
        findings=findings,
        required_tests_checks=[
            "Add at least one failure-mode test for stale paths, stale artifacts, and output schema drift.",
        ],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane derives test targets from preflight inventory and the repository tree.",
    )
