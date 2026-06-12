from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .lane_runners_common import lane_payload, repo_files
from .workspace import read_text


def scientific_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    doc_files = repo_files(root, {".md", ".mdx", ".rst", ".txt", ".qmd"})
    text = "\n".join(read_text(root / path) for path in doc_files)
    causal_pattern = r"\b(causes?|causal|effect|impact|proves?|predicts?|prognostic)\b"
    causal_terms = sorted(set(re.findall(causal_pattern, text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if causal_terms:
        findings.append(
            {
                "title": "Interpretive claim language needs design support check",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": (
                    "Public or project docs include causal, predictive, or prognostic language that "
                    "must be checked against design and validation evidence."
                ),
                "lane": "scientific-reviewer",
            }
        )
        actions.append(
            "Classify each claim as descriptive, associational, causal, predictive, or prognostic "
            "before reporting it."
        )
    return lane_payload(
        lane="scientific-reviewer",
        root=root,
        artifact_map={"doc_files": doc_files, "claim_terms": causal_terms},
        findings=findings,
        required_tests_checks=[
            "Verify cohort definition, measurement validity, bias risks, and external validity "
            "before accepting interpretation.",
        ],
        recommended_actions=actions,
        direct_evidence_vs_inference=(
            "This lane is grounded in local prose and flags claim language that requires "
            "scientific interpretation review."
        ),
    )
