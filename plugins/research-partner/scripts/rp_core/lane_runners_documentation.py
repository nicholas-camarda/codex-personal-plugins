from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload


def run_documentation_wizard_lane(root: Path, documentation_wizard_script: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(documentation_wizard_script), "report", "--repo", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise ValueError("documentation-wizard returned a non-object payload")

    findings = []
    for finding in payload.get("findings", []):
        if isinstance(finding, dict):
            enriched = dict(finding)
            enriched.setdefault("title", enriched.get("kind", "Documentation finding"))
            enriched.setdefault("severity", "P2")
            enriched.setdefault("evidence_basis", "Direct")
            enriched["lane"] = "documentation-wizard"
            findings.append(enriched)
    return lane_payload(
        lane="documentation-wizard",
        root=root,
        artifact_map={
            "documentation_wizard_script": str(documentation_wizard_script),
            "documentation_report_scope": payload.get("scope"),
            "documentation_artifact_map": payload.get("artifact_map", {}),
        },
        findings=findings,
        required_tests_checks=list(payload.get("required_tests_checks", [])),
        recommended_actions=list(payload.get("recommended_actions", [])),
        direct_evidence_vs_inference=str(
            payload.get(
                "direct_evidence_vs_inference",
                "Documentation findings are grounded in documentation-wizard output.",
            )
        ),
    )
