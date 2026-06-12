from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .workspace import read_text

IGNORED_WALK_DIRS = {
    ".git",
    ".history",
    ".codex",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "migration_backups",
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def lane_payload(
    *,
    lane: str,
    root: Path,
    artifact_map: dict[str, Any],
    findings: list[dict[str, Any]],
    required_tests_checks: list[str],
    recommended_actions: list[str],
    direct_evidence_vs_inference: str,
) -> dict[str, Any]:
    return {
        "scope": "research-review-lane",
        "lane": lane,
        "artifact_map": {"repo_root": str(root), **artifact_map},
        "findings": findings,
        "direct_evidence_vs_inference": direct_evidence_vs_inference,
        "required_tests_checks": required_tests_checks,
        "recommended_actions": recommended_actions,
    }


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


def _repo_files(root: Path, suffixes: set[str]) -> list[str]:
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_WALK_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() in suffixes:
                paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


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


def stats_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    analysis_files = _repo_files(root, {".py", ".r", ".qmd", ".ipynb"})
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


def scientific_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    doc_files = _repo_files(root, {".md", ".mdx", ".rst", ".txt", ".qmd"})
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


def execute_lane(
    lane: str,
    root: Path,
    preflight: dict[str, Any],
    documentation_wizard_script: Path,
) -> dict[str, Any]:
    if lane == "documentation-wizard":
        return run_documentation_wizard_lane(root, documentation_wizard_script)
    if lane == "implementation-auditor":
        return implementation_auditor_lane(root, preflight)
    if lane == "stats-reviewer":
        return stats_reviewer_lane(root, preflight)
    if lane == "scientific-reviewer":
        return scientific_reviewer_lane(root, preflight)
    if lane == "literature-support-reviewer":
        return literature_support_lane(root, preflight)
    if lane == "robustness-test-designer":
        return robustness_test_designer_lane(root, preflight)
    raise ValueError(f"Unknown lane: {lane}")


def run_review(
    repo_root: Path,
    output_dir: Path,
    lanes: list[str] | None,
    *,
    executable_lanes: list[str],
    inventory_func,
    bundle_func,
    documentation_wizard_script: Path,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    selected_lanes = lanes or executable_lanes
    unknown = sorted(set(selected_lanes) - set(executable_lanes))
    if unknown:
        raise ValueError(f"Unknown lanes requested: {', '.join(unknown)}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = inventory_func(root)
    preflight_path = output_dir / "preflight.json"
    write_json(preflight_path, preflight)

    lane_paths: list[Path] = []
    lane_outputs: list[dict[str, Any]] = []
    for lane in selected_lanes:
        payload = execute_lane(lane, root, preflight, documentation_wizard_script)
        lane_path = output_dir / f"{lane}.json"
        write_json(lane_path, payload)
        lane_paths.append(lane_path)
        lane_outputs.append({"lane": lane, "path": str(lane_path), "finding_count": len(payload.get("findings", []))})

    bundle = bundle_func(preflight_path, lane_paths)
    bundle.update(
        {
            "command": "run",
            "status": "ok",
            "scope": "multi-lane-review",
            "repo_root": str(root),
            "output_dir": str(output_dir),
            "preflight_path": str(preflight_path),
            "lane_outputs": lane_outputs,
        }
    )
    bundle_path = output_dir / "bundle.json"
    write_json(bundle_path, bundle)
    bundle["bundle_path"] = str(bundle_path)
    return bundle
