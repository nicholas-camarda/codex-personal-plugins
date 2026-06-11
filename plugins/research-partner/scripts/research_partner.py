#!/usr/bin/env python3
"""Helper CLI for research-partner."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_SKILLS = [
    "assess-literature-support",
    "design-robustness-tests",
    "inspect-analysis-artifacts",
    "research-partner",
    "review-documentation-consistency",
    "review-implementation-validity",
    "review-scientific-interpretation",
    "review-statistical-validity",
    "synthesize-review",
]

PLUGIN_NAME = "research-partner"
PLUGIN_DISPLAY_NAME = "Research Partner"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME
WORKSPACE_SOURCE_NAME = "workspace-governor dry-run"
HOME = Path.home()
ONEDRIVE_ROOT = Path(os.environ.get("CODEX_ONEDRIVE_ROOT", HOME / "Library" / "CloudStorage" / "OneDrive-Personal")).expanduser()
PROJECTS_ROOT = Path(os.environ.get("CODEX_PROJECTS_ROOT", HOME / "Projects")).expanduser()
RUNTIME_ROOT = Path(os.environ.get("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")).expanduser()
RESEARCH_ROOT = Path(os.environ.get("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")).expanduser()
SIDEPROJECTS_ROOT = Path(os.environ.get("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")).expanduser()
LEGACY_ROOT = Path(os.environ.get("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")).expanduser()
CANONICAL_ROOTS = (PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT)

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

EXECUTABLE_LANES = [
    "documentation-wizard",
    "implementation-auditor",
    "stats-reviewer",
    "scientific-reviewer",
    "literature-support-reviewer",
    "robustness-test-designer",
]

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
DECLARED_PATH_HINTS = (
    "/Users/",
    "/mnt/",
    "C:\\",
    "~/Projects",
    "~/ProjectsRuntime",
    "SideProjects/",
    "Research/",
    "OneDrive",
)
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


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def is_relative_to(path: Path, candidate: Path) -> bool:
    try:
        path.relative_to(candidate)
    except ValueError:
        return False
    return True


def peer_plugin_root(plugin_name: str) -> Path:
    env_key = f"CODEX_{plugin_name.upper().replace('-', '_')}_PLUGIN_ROOT"
    candidate_roots: list[Path] = []

    explicit_root = os.environ.get(env_key)
    if explicit_root:
        candidate_roots.append(Path(explicit_root).expanduser())

    plugins_root = os.environ.get("CODEX_PLUGINS_ROOT")
    if plugins_root:
        candidate_roots.append(Path(plugins_root).expanduser() / plugin_name)

    current_plugin_root = Path(__file__).resolve().parents[1]
    candidate_roots.extend(
        [
            current_plugin_root.parent / plugin_name,
            HOME / ".codex" / "plugins" / plugin_name,
        ]
    )

    seen: set[str] = set()
    fallback = candidate_roots[-1]
    for candidate in candidate_roots:
        marker = str(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        if candidate.exists():
            return candidate.resolve()
        fallback = candidate
    return fallback


def peer_plugin_script(plugin_name: str, script_name: str) -> Path:
    return peer_plugin_root(plugin_name) / "scripts" / script_name


WORKSPACE_GOVERNOR_SCRIPT = peer_plugin_script("workspace-governor", "workspace_governor.py")


def marketplace_root(path: Path) -> Path:
    return path.parents[2]


def marketplace_entry_by_name(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any] | None:
    for item in marketplace.get("plugins", []):
        if isinstance(item, dict) and item.get("name") == plugin_name:
            return item
    return None


def marketplace_entry_has_required_metadata(entry: dict[str, Any] | None) -> bool:
    if not isinstance(entry, dict):
        return False
    source = entry.get("source")
    policy = entry.get("policy")
    return (
        isinstance(source, dict)
        and source.get("source") == "local"
        and isinstance(source.get("path"), str)
        and str(source.get("path")).startswith("./")
        and isinstance(policy, dict)
        and isinstance(policy.get("installation"), str)
        and isinstance(policy.get("authentication"), str)
        and isinstance(entry.get("category"), str)
    )


def marketplace_entry_resolves_to(
    entry: dict[str, Any] | None,
    marketplace_path: Path | None,
    target_path: Path,
) -> bool:
    if not isinstance(entry, dict) or marketplace_path is None:
        return False
    source = entry.get("source")
    if not isinstance(source, dict):
        return False
    relative_path = source.get("path")
    if not isinstance(relative_path, str) or not relative_path.startswith("./"):
        return False
    resolved_target = (marketplace_root(marketplace_path) / relative_path[2:]).resolve()
    return resolved_target == target_path.resolve()


def parse_declared_path(line: str) -> Path | None:
    normalized = line.replace("`", "").strip()
    match = re.search(r"(~/[^\s,;`]+|/(?!/)[^\s,;`]+|[A-Za-z]:\\[^\s,;`]+)", normalized)
    if not match:
        return None
    candidate = match.group(1).rstrip(".,:;)")
    if candidate.startswith("~/"):
        return Path(candidate).expanduser()
    if candidate.startswith("/"):
        return Path(candidate)
    if re.match(r"^[A-Za-z]:\\", candidate):
        return None
    return None


def default_workspace_path_review(status: str = "not-needed") -> dict[str, Any]:
    return {
        "status": status,
        "source": None,
        "topology_mode": "generic-repo",
        "topology_confidence": "low",
        "topology_evidence": [],
        "proposed_code_root": None,
        "proposed_runtime_root": None,
        "proposed_cloud_home": None,
        "doc_contract_passed": None,
        "rewrite_candidate_count": 0,
        "question_count": 0,
    }


def classify_workspace_topology(
    root: Path,
    declared_paths: list[str],
    findings: list[dict[str, Any]],
    project_doc_exists: bool,
    registry_exists: bool,
    scripts: list[str],
    notebooks: list[str],
    data_dirs: set[str],
) -> tuple[str, str, list[str], bool]:
    evidence: list[str] = []
    score = 0

    if any(is_relative_to(root, candidate) for candidate in CANONICAL_ROOTS):
        score += 3
        evidence.append("repo lives under a canonical research workspace root")
    if is_relative_to(root, LEGACY_ROOT):
        score += 2
        evidence.append("repo lives under the legacy research workspace root")
    if declared_paths:
        score += 3
        evidence.append("project metadata declares absolute or home-relative paths")
    if any((item.get("title") or "").startswith("Declared path missing:") for item in findings):
        score += 2
        evidence.append("project metadata references a missing declared path")
    if project_doc_exists:
        score += 1
        evidence.append("AGENTS.md is present")
    if registry_exists:
        score += 1
        evidence.append("analysis_registry.yaml is present")
    if scripts:
        score += 1
        evidence.append("scripts or tests were discovered")
    if notebooks or data_dirs:
        score += 1
        evidence.append("analysis artifacts such as notebooks or data directories were discovered")

    if score >= 6:
        return "research-layout", "high", evidence, True
    if score >= 3:
        return "research-layout", "medium", evidence, True
    return "generic-repo", "low", evidence, False


def run_workspace_governor_dry_run(root: Path) -> dict[str, Any]:
    summary = default_workspace_path_review("unavailable")
    summary["source"] = WORKSPACE_SOURCE_NAME
    if not WORKSPACE_GOVERNOR_SCRIPT.exists():
        return {"summary": summary, "status": "unavailable", "payload": None}

    try:
        proc = subprocess.run(
            [sys.executable, str(WORKSPACE_GOVERNOR_SCRIPT), "dry-run", "--repo", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise ValueError("workspace-governor returned a non-object payload")
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError, ValueError):
        summary["status"] = "error"
        return {"summary": summary, "status": "error", "payload": None}

    summary.update(
        {
            "status": "ok",
            "proposed_code_root": payload.get("proposed_code_root"),
            "proposed_runtime_root": payload.get("proposed_runtime_root"),
            "proposed_cloud_home": payload.get("proposed_cloud_home"),
            "doc_contract_passed": payload.get("doc_contract", {}).get("passed"),
            "rewrite_candidate_count": len(payload.get("rewrite_candidates", [])),
            "question_count": len(payload.get("questions", [])),
        }
    )
    return {"summary": summary, "status": "ok", "payload": payload}


def build_generic_workspace_path_review(evidence: list[str]) -> dict[str, Any]:
    summary = default_workspace_path_review("not-needed")
    summary["source"] = "generic-repo heuristic"
    summary["topology_evidence"] = evidence
    return summary


def add_unique_action(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


def append_workspace_findings(
    findings: list[dict[str, Any]],
    recommended_actions: list[str],
    workspace_review: dict[str, Any],
) -> None:
    status = workspace_review["summary"]["status"]
    payload = workspace_review["payload"] or {}

    if status in {"error", "unavailable"}:
        findings.append(
            {
                "title": "Workspace audit evidence unavailable",
                "severity": "P2",
                "evidence_basis": "Missing",
                "message": "The workspace-governor dry-run handoff did not produce usable path-topology evidence.",
            }
        )
        add_unique_action(recommended_actions, "Restore workspace-governor dry-run evidence before trusting workspace path assumptions.")
        return

    if payload.get("questions"):
        findings.append(
            {
                "title": "Workspace topology remains unresolved",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "workspace-governor dry-run reported unresolved workspace questions that should be answered before specialist review relies on path assumptions.",
            }
        )
        add_unique_action(recommended_actions, "Review the workspace-governor dry-run questions before running specialist review lanes.")

    if payload.get("doc_contract", {}).get("passed") is False:
        findings.append(
            {
                "title": "Public/private doc contract is incomplete",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "workspace-governor dry-run found that the repo does not fully satisfy the README plus AGENTS.md documentation split.",
            }
        )
        add_unique_action(recommended_actions, "Fix the README and AGENTS.md doc contract before relying on published path guidance.")

    if payload.get("rewrite_candidates"):
        findings.append(
            {
                "title": "Stale hard-coded path assumptions detected",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "workspace-governor dry-run found path rewrite candidates that may invalidate implementation or methods assumptions.",
            }
        )
        add_unique_action(recommended_actions, "Review workspace-governor rewrite candidates before interpreting path-sensitive outputs.")


def inventory_repo(root: Path) -> dict[str, Any]:
    project_doc = root / "AGENTS.md"
    registry = root / "analysis_registry.yaml"
    scripts: list[str] = []
    notebooks: list[str] = []
    data_dirs: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_WALK_DIRS]
        current = Path(dirpath)
        rel_dir = current.relative_to(root)
        if rel_dir != Path(".") and current.name in {"data", "output", "outputs", "results", "reports", "final"}:
            data_dirs.add(rel_dir.as_posix())
        for filename in filenames:
            path = current / filename
            rel_path = path.relative_to(root).as_posix()
            if current.name in {"scripts", "tests"}:
                scripts.append(rel_path)
            if path.suffix.lower() == ".ipynb":
                notebooks.append(rel_path)
    text = read_text(project_doc) + "\n" + read_text(registry)
    declared_paths = sorted({line.strip() for line in text.splitlines() if parse_declared_path(line) is not None or any(hint in line for hint in DECLARED_PATH_HINTS)})

    findings = []
    for path in declared_paths:
        candidate = parse_declared_path(path)
        if candidate is None:
            continue
        if not candidate.exists():
            findings.append(
                {
                    "title": f"Declared path missing: {candidate}",
                    "severity": "P2",
                    "evidence_basis": "Direct",
                    "message": "A path declared in project metadata does not exist locally.",
                }
            )

    recommended_actions: list[str] = []
    if findings:
        add_unique_action(recommended_actions, "Resolve missing declared paths before running specialist review lanes.")
    topology_mode, topology_confidence, topology_evidence, should_run_workspace_handoff = classify_workspace_topology(
        root,
        declared_paths,
        findings,
        project_doc.exists(),
        registry.exists(),
        scripts,
        notebooks,
        data_dirs,
    )
    workspace_path_review = build_generic_workspace_path_review(topology_evidence)
    workspace_path_review["topology_mode"] = topology_mode
    workspace_path_review["topology_confidence"] = topology_confidence
    if should_run_workspace_handoff:
        workspace_review = run_workspace_governor_dry_run(root)
        workspace_path_review = workspace_review["summary"]
        workspace_path_review["topology_mode"] = topology_mode
        workspace_path_review["topology_confidence"] = topology_confidence
        workspace_path_review["topology_evidence"] = topology_evidence
        append_workspace_findings(findings, recommended_actions, workspace_review)
    if not findings and not recommended_actions:
        add_unique_action(recommended_actions, "Proceed to specialist review lanes.")

    return {
        "scope": "analysis-review-preflight",
        "artifact_map": {
            "repo_root": str(root),
            "project_doc": str(project_doc) if project_doc.exists() else None,
            "analysis_registry": str(registry) if registry.exists() else None,
            "scripts_and_tests": sorted(scripts),
            "notebooks": sorted(notebooks),
            "data_like_dirs": sorted(data_dirs),
            "declared_paths": declared_paths,
            "workspace_path_review": workspace_path_review,
        },
        "findings": findings,
        "direct_evidence_vs_inference": "Inventory findings are grounded in the repo tree and declared project metadata.",
        "required_tests_checks": ["Confirm that declared runtime and published-output paths match the actual environment."],
        "recommended_actions": recommended_actions,
        "flow": DEFAULT_FLOW,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


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


def run_documentation_wizard_lane(root: Path) -> dict[str, Any]:
    script = peer_plugin_script("documentation-wizard", "documentation_wizard.py")
    proc = subprocess.run(
        [sys.executable, str(script), "report", "--repo", str(root)],
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
            "documentation_wizard_script": str(script),
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
    test_files = [path for path in scripts if "/tests/" in f"/{path}" or path.startswith("tests/") or Path(path).name.startswith("test_")]
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
        actions.append("Add tests or smoke checks for the executable analysis scripts before trusting implementation claims.")
    return lane_payload(
        lane="implementation-auditor",
        root=root,
        artifact_map={"code_files": code_files, "test_files": test_files},
        findings=findings,
        required_tests_checks=["Run the analysis smoke command and the repository test suite, if present."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane is grounded in files discovered by preflight; method correctness still requires manual code review.",
    )


def stats_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    analysis_files = _repo_files(root, {".py", ".r", ".qmd", ".ipynb"})
    text = "\n".join(read_text(root / path) for path in analysis_files if not path.endswith(".ipynb"))
    method_terms = sorted(set(re.findall(r"\b(cox|logistic|linear|regression|bootstrap|kaplan|survival|auc|calibration|pvalue|p-value)\b", text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if analysis_files and not method_terms:
        findings.append(
            {
                "title": "Statistical method target is not explicit in code text",
                "severity": "P3",
                "evidence_basis": "Inference",
                "message": "Analysis files were present, but the lightweight scan did not find explicit statistical method terms.",
                "lane": "stats-reviewer",
            }
        )
        actions.append("Identify the estimand or prediction target and verify the statistical method manually.")
    return lane_payload(
        lane="stats-reviewer",
        root=root,
        artifact_map={"analysis_files": analysis_files, "method_terms": method_terms},
        findings=findings,
        required_tests_checks=["Check estimand alignment, outcome type, missingness handling, calibration, and sensitivity analyses."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane uses a lightweight repository scan and flags missing evidence; it does not replace a full statistical review.",
    )


def scientific_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    doc_files = _repo_files(root, {".md", ".mdx", ".rst", ".txt", ".qmd"})
    text = "\n".join(read_text(root / path) for path in doc_files)
    causal_terms = sorted(set(re.findall(r"\b(causes?|causal|effect|impact|proves?|predicts?|prognostic)\b", text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if causal_terms:
        findings.append(
            {
                "title": "Interpretive claim language needs design support check",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "Public or project docs include causal, predictive, or prognostic language that must be checked against design and validation evidence.",
                "lane": "scientific-reviewer",
            }
        )
        actions.append("Classify each claim as descriptive, associational, causal, predictive, or prognostic before reporting it.")
    return lane_payload(
        lane="scientific-reviewer",
        root=root,
        artifact_map={"doc_files": doc_files, "claim_terms": causal_terms},
        findings=findings,
        required_tests_checks=["Verify cohort definition, measurement validity, bias risks, and external validity before accepting interpretation."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane is grounded in local prose and flags claim language that requires scientific interpretation review.",
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
                "message": "No analysis_registry.yaml was discovered, so domain and method context for literature support is incomplete.",
                "lane": "literature-support-reviewer",
            }
        )
        actions.append("Add or update analysis_registry.yaml with project type, domain, and analysis context before literature support review.")
    return lane_payload(
        lane="literature-support-reviewer",
        root=root,
        artifact_map={"analysis_registry": registry_path},
        findings=findings,
        required_tests_checks=["Tie any literature citation to the actual design, population, endpoint, and implementation details."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane checks whether enough local context exists for a literature support review; it does not perform external literature search.",
    )


def robustness_test_designer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    scripts = list(preflight.get("artifact_map", {}).get("scripts_and_tests", []))
    findings: list[dict[str, Any]] = []
    actions = [
        "Add regression tests for artifact presence, schema stability, documented path assumptions, and one representative analysis smoke run."
    ]
    if scripts:
        findings.append(
            {
                "title": "Robustness test targets identified",
                "severity": "P3",
                "evidence_basis": "Direct",
                "message": "Executable files were found and should be covered by smoke or regression tests tied to scientific failure modes.",
                "lane": "robustness-test-designer",
            }
        )
    return lane_payload(
        lane="robustness-test-designer",
        root=root,
        artifact_map={"scripts_and_tests": scripts},
        findings=findings,
        required_tests_checks=["Add at least one failure-mode test for stale paths, stale artifacts, and output schema drift."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane derives test targets from preflight inventory and the repository tree.",
    )


def execute_lane(lane: str, root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    if lane == "documentation-wizard":
        return run_documentation_wizard_lane(root)
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


def run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    selected_lanes = lanes or EXECUTABLE_LANES
    unknown = sorted(set(selected_lanes) - set(EXECUTABLE_LANES))
    if unknown:
        raise ValueError(f"Unknown lanes requested: {', '.join(unknown)}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = inventory_repo(root)
    preflight_path = output_dir / "preflight.json"
    write_json(preflight_path, preflight)

    lane_paths: list[Path] = []
    lane_outputs: list[dict[str, Any]] = []
    for lane in selected_lanes:
        payload = execute_lane(lane, root, preflight)
        lane_path = output_dir / f"{lane}.json"
        write_json(lane_path, payload)
        lane_paths.append(lane_path)
        lane_outputs.append({"lane": lane, "path": str(lane_path), "finding_count": len(payload.get("findings", []))})

    bundle = bundle_review(preflight_path, lane_paths)
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
            if existing is None or SEVERITY_ORDER.get(finding.get("severity", "P3"), 3) < SEVERITY_ORDER.get(existing.get("severity", "P3"), 3):
                merged[finding_key(finding)] = finding
    for finding in preflight.get("findings", []):
        if isinstance(finding, dict):
            merged.setdefault(finding_key(finding), finding)

    findings = sorted(merged.values(), key=lambda item: (SEVERITY_ORDER.get(item.get("severity", "P3"), 3), item.get("title") or item.get("message") or ""))
    recommended_actions = []
    for lane in [preflight, *lanes]:
        for action in lane.get("recommended_actions", []):
            if action not in recommended_actions:
                recommended_actions.append(action)

    return {
        "scope": preflight.get("scope", "multi-lane-review"),
        "artifact_map": artifact_map,
        "findings": findings,
        "direct_evidence_vs_inference": "This bundle preserves each lane's evidence basis and deduplicates overlapping findings by lane and title/message.",
        "required_tests_checks": sorted({check for lane in [preflight, *lanes] for check in lane.get("required_tests_checks", [])}),
        "recommended_actions": recommended_actions,
        "flow": DEFAULT_FLOW,
        "evidence_bundle": evidence_sources,
    }


def validate_plugin(root: Path) -> dict[str, Any]:
    plugin_root = root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    source_marketplace_path = plugin_root.parents[1] / ".agents" / "plugins" / "marketplace.json"
    source_checkout = plugin_root.parent.name == "plugins" and source_marketplace_path.exists()
    marketplace_path = source_marketplace_path if source_checkout else HOME_MARKETPLACE_PATH
    marketplace = load_json(marketplace_path) if marketplace_path.exists() else {}
    expected_plugin_root = plugin_root if source_checkout else HOME_PLUGIN_ROOT
    readme_text = read_text(plugin_root / "README.md")
    top_level_skill = read_text(plugin_root / "skills" / "research-partner" / "SKILL.md")
    docs_wizard_skill = peer_plugin_root("documentation-wizard") / "skills" / "documentation-wizard" / "SKILL.md"
    workspace_governor_script = peer_plugin_script("workspace-governor", "workspace_governor.py")

    checks = []

    registered_entry = marketplace_entry_by_name(marketplace, PLUGIN_NAME)
    checks.append({"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME})
    checks.append({"name": "display-name", "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME})
    checks.append({"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH})
    checks.append({"name": "marketplace-registration", "passed": registered_entry is not None})
    checks.append(
        {
            "name": "marketplace-entry-path",
            "passed": marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        }
    )
    checks.append({"name": "marketplace-entry-metadata", "passed": marketplace_entry_has_required_metadata(registered_entry)})
    checks.append({"name": "plugin-root-is-source-or-home-root", "passed": plugin_root.resolve() == expected_plugin_root.resolve()})
    checks.append({"name": "plugin-manifest-exists", "passed": manifest_path.exists()})
    checks.append({"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)})
    checks.append({"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill})
    checks.append(
        {
            "name": "default-flow",
            "passed": "review-preflight" in top_level_skill and "documentation-wizard" in top_level_skill and "review-synthesizer" in top_level_skill,
        }
    )
    checks.append({"name": "mention-docs", "passed": "@research-partner" in readme_text})
    checks.append({"name": "docs-lane-dependency", "passed": docs_wizard_skill.exists()})
    checks.append({"name": "workspace-governor-dependency", "passed": workspace_governor_script.exists()})
    checks.append(
        {
            "name": "workspace-handoff-docs",
            "passed": "workspace-governor" in readme_text and "workspace-governor" in top_level_skill,
        }
    )

    for skill_name in REQUIRED_SKILLS:
        checks.append(
            {
                "name": f"skill:{skill_name}",
                "passed": (plugin_root / "skills" / skill_name / "SKILL.md").exists(),
            }
        )

    composer_icon = manifest.get("interface", {}).get("composerIcon")
    logo = manifest.get("interface", {}).get("logo")
    icon_path = plugin_root / composer_icon.replace("./", "") if isinstance(composer_icon, str) else None
    logo_path = plugin_root / logo.replace("./", "") if isinstance(logo, str) else None
    checks.append({"name": "icon-exists", "passed": icon_path.exists() if icon_path else False})
    checks.append({"name": "logo-exists", "passed": logo_path.exists() if logo_path else False})

    passed = all(check["passed"] for check in checks)
    return {"plugin": "research-partner", "passed": passed, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="research-partner helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Inventory repo artifacts before review")
    inventory_parser.add_argument("--repo", required=True)

    bundle_parser = subparsers.add_parser("bundle", help="Bundle preflight and lane outputs")
    bundle_parser.add_argument("--preflight", required=True)
    bundle_parser.add_argument("--lane", action="append", default=[])

    run_parser = subparsers.add_parser("run", help="Run preflight, execute review lanes, and bundle results")
    run_parser.add_argument("--repo", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--lane", action="append", default=[])

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    args = parser.parse_args()
    if args.command == "inventory":
        payload = inventory_repo(Path(args.repo).expanduser().resolve())
    elif args.command == "bundle":
        payload = bundle_review(Path(args.preflight).resolve(), [Path(item).resolve() for item in args.lane])
    elif args.command == "run":
        payload = run_review(
            repo_root=Path(args.repo),
            output_dir=Path(args.output_dir),
            lanes=args.lane or None,
        )
    else:
        payload = validate_plugin(Path(__file__).resolve().parent)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
