#!/usr/bin/env python3
"""Helper CLI for research-partner."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rp_core.bundles import DEFAULT_FLOW, bundle_review, finding_key, load_json
from rp_core.lanes import IGNORED_WALK_DIRS, run_review as run_review_impl
from rp_core.workspace import (
    append_workspace_findings,
    classify_workspace_topology,
    default_workspace_path_review,
    parse_declared_path,
    read_text,
    run_workspace_governor_dry_run,
)

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
HOME = Path.home()

EXECUTABLE_LANES = [
    "documentation-wizard",
    "implementation-auditor",
    "stats-reviewer",
    "scientific-reviewer",
    "literature-support-reviewer",
    "robustness-test-designer",
]

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


def build_generic_workspace_path_review(evidence: list[str]) -> dict[str, Any]:
    summary = default_workspace_path_review("not-needed")
    summary["source"] = "generic-repo heuristic"
    summary["topology_evidence"] = evidence
    return summary


def add_unique_action(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


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
    declared_paths = sorted(
        {
            line.strip()
            for line in text.splitlines()
            if parse_declared_path(line) is not None or any(hint in line for hint in DECLARED_PATH_HINTS)
        }
    )

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
        workspace_review = run_workspace_governor_dry_run(root, WORKSPACE_GOVERNOR_SCRIPT)
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
        "direct_evidence_vs_inference": (
            "Inventory findings are grounded in the repo tree and declared project metadata."
        ),
        "required_tests_checks": [
            "Confirm that declared runtime and published-output paths match the actual environment.",
        ],
        "recommended_actions": recommended_actions,
        "flow": DEFAULT_FLOW,
    }


def run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None) -> dict[str, Any]:
    return run_review_impl(
        repo_root,
        output_dir,
        lanes,
        executable_lanes=EXECUTABLE_LANES,
        inventory_func=inventory_repo,
        bundle_func=bundle_review,
        documentation_wizard_script=peer_plugin_script("documentation-wizard", "documentation_wizard.py"),
    )


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
    checks.append(
        {
            "name": "display-name",
            "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME,
        }
    )
    checks.append({"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH})
    checks.append({"name": "marketplace-registration", "passed": registered_entry is not None})
    checks.append(
        {
            "name": "marketplace-entry-path",
            "passed": marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        }
    )
    checks.append(
        {
            "name": "marketplace-entry-metadata",
            "passed": marketplace_entry_has_required_metadata(registered_entry),
        }
    )
    checks.append(
        {
            "name": "plugin-root-is-source-or-home-root",
            "passed": plugin_root.resolve() == expected_plugin_root.resolve(),
        }
    )
    checks.append({"name": "plugin-manifest-exists", "passed": manifest_path.exists()})
    checks.append({"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)})
    checks.append({"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill})
    checks.append(
        {
            "name": "default-flow",
            "passed": (
                "review-preflight" in top_level_skill
                and "documentation-wizard" in top_level_skill
                and "review-synthesizer" in top_level_skill
            ),
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
