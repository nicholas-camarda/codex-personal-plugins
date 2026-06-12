from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload, repo_files
from .workspace import read_text


def stats_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    analysis_files = repo_files(root, {".py", ".r", ".qmd", ".ipynb"})
    text = "\n".join(read_text(root / path) for path in analysis_files if not path.endswith(".ipynb"))
    method_pattern = (
        r"\b(cox|logistic|linear|regression|bootstrap|kaplan|survival|auc|calibration|pvalue|p-value)\b"
    )
    method_terms = sorted(set(re.findall(method_pattern, text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if analysis_files and not method_terms:
        findings.append(
            {
                "title": "Statistical method target is not explicit in code text",
                "severity": "P3",
                "evidence_basis": "Inference",
                "message": (
                    "Analysis files were present, but the lightweight scan did not find explicit "
                    "statistical method terms."
                ),
                "lane": "stats-reviewer",
            }
        )
        actions.append("Identify the estimand or prediction target and verify the statistical method manually.")
    return lane_payload(
        lane="stats-reviewer",
        root=root,
        artifact_map={"analysis_files": analysis_files, "method_terms": method_terms},
        findings=findings,
        required_tests_checks=[
            "Check estimand alignment, outcome type, missingness handling, calibration, and sensitivity analyses.",
        ],
        recommended_actions=actions,
        direct_evidence_vs_inference=(
            "This lane uses a lightweight repository scan and flags missing evidence; "
            "it does not replace a full statistical review."
        ),
    )
