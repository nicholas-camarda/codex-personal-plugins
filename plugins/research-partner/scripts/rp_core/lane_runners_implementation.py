from __future__ import annotations

from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload


def implementation_auditor_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    scripts = list(preflight.get("artifact_map", {}).get("scripts_and_tests", []))
    test_files = [
        path
        for path in scripts
        if "/tests/" in f"/{path}" or path.startswith("tests/") or Path(path).name.startswith("test_")
    ]
    code_files = [path for path in scripts if path.endswith((".py", ".R", ".r", ".sh")) and path not in test_files]
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if code_files and not test_files:
        findings.append(
            {
                "title": "Executable analysis code lacks discovered tests",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "Preflight found scripts but no test files, so implementation validity is weakly protected.",
                "lane": "implementation-auditor",
            }
        )
        actions.append(
            "Add tests or smoke checks for the executable analysis scripts before trusting "
            "implementation claims."
        )
    return lane_payload(
        lane="implementation-auditor",
        root=root,
        artifact_map={"code_files": code_files, "test_files": test_files},
        findings=findings,
        required_tests_checks=["Run the analysis smoke command and the repository test suite, if present."],
        recommended_actions=actions,
        direct_evidence_vs_inference=(
            "This lane is grounded in files discovered by preflight; method correctness still "
            "requires manual code review."
        ),
    )
