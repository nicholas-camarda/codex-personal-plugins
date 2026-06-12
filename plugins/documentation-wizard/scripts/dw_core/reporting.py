from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

from .files import DOC_SUFFIXES, is_public_doc, iter_files, read_text, relative
from .interfaces import FLAG_RE, extract_interfaces, locate_line
from .sanitize import find_private_infra_leaks, sanitize_public_docs


BACKTICK_RE = re.compile(r"`([^`]+)`")
SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_denylist",
}


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def analysis_registry_review(root: Path) -> dict[str, Any]:
    path = root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "exists": False,
            "path": "analysis_registry.yaml",
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
        }
    keys = top_level_yaml_keys(read_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    return {
        "exists": True,
        "path": "analysis_registry.yaml",
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
    }


def inventory_docs(root: Path) -> dict[str, Any]:
    doc_surfaces = []
    for path in iter_files(root, DOC_SUFFIXES):
        rel = relative(path, root)
        if rel.startswith("docs/") or path.name.upper().startswith(("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")):
            doc_surfaces.append(rel)

    source_truth = []
    for path in iter_files(root, {".py", ".json"}):
        text = read_text(path)
        rel = relative(path, root)
        if "add_argument(" in text:
            source_truth.append({"kind": "cli", "path": rel})
        if path.name.endswith(".schema.json"):
            source_truth.append({"kind": "config-schema", "path": rel})
    if (root / "AGENTS.md").exists():
        source_truth.append({"kind": "ops-metadata", "path": "AGENTS.md"})
    registry_review = analysis_registry_review(root)
    if registry_review["exists"] and registry_review["supported"]:
        source_truth.append({"kind": "repo-metadata", "path": "analysis_registry.yaml"})

    return {
        "repo_root": str(root),
        "doc_surfaces": doc_surfaces,
        "public_doc_surfaces": [rel for rel in doc_surfaces if is_public_doc(rel)],
        "source_truth_candidates": source_truth,
        "analysis_registry_review": registry_review,
    }


def documented_tokens(root: Path) -> dict[str, dict[str, str]]:
    flags: dict[str, str] = {}
    config_keys: dict[str, str] = {}
    for rel_path in inventory_docs(root)["public_doc_surfaces"]:
        path = root / rel_path
        text = read_text(path)
        for flag in FLAG_RE.findall(text):
            flags.setdefault(flag, f"{rel_path}:{locate_line(path, flag) or 1}")
        for token in BACKTICK_RE.findall(text):
            if "/" in token or token.startswith("--"):
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", token):
                config_keys.setdefault(token, f"{rel_path}:{locate_line(path, token) or 1}")
    return {"flags": flags, "config_keys": config_keys}


def closest_match(token: str, candidates: list[str]) -> str | None:
    matches = difflib.get_close_matches(token, candidates, n=1, cutoff=0.5)
    return matches[0] if matches else None


def build_report(root: Path) -> dict[str, Any]:
    inventory = inventory_docs(root)
    interfaces = extract_interfaces(root)
    docs = documented_tokens(root)

    cli_flags = {item["flag"]: item for item in interfaces["cli_flags"]}
    config_keys = {item["key"]: item for item in interfaces["config_keys"]}
    findings: list[dict[str, Any]] = []
    registry_review = inventory.get("analysis_registry_review") or {}

    if registry_review.get("exists") and not registry_review.get("supported", True):
        unsupported = ", ".join(registry_review.get("unsupported_top_level_keys") or [])
        findings.append(
            {
                "kind": "unsupported-analysis-registry-shape",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": "analysis_registry.yaml",
                "source_ref": "analysis_registry.yaml",
                "message": f"analysis_registry.yaml uses unsupported top-level keys ({unsupported}).",
                "impact": "Tooling may silently ignore most of the file and leave misleading metadata in place.",
                "patch_direction": (
                    "Rewrite analysis_registry.yaml to the supported top-level metadata contract: "
                    "project_slug, project_type, domain, cloud_home, runtime_home, publish_root_name, publish_denylist."
                ),
            }
        )

    for flag, doc_ref in docs["flags"].items():
        if flag in cli_flags:
            continue
        suggestion = closest_match(flag, sorted(cli_flags))
        doc_name = doc_ref.split(":", 1)[0]
        if suggestion:
            patch = f"Replace `{flag}` with `{suggestion}` in {doc_name}"
        else:
            patch = f"Remove or correct `{flag}` in {doc_name}"
        findings.append(
            {
                "kind": "stale-cli-flag",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": cli_flags.get(suggestion, {}).get("source_ref") if suggestion else "missing-live-flag",
                "message": f"Documented flag `{flag}` does not appear in the live CLI surface.",
                "impact": "Users may copy a command that no longer parses.",
                "patch_direction": patch,
            }
        )

    for flag, source in cli_flags.items():
        if flag in docs["flags"]:
            continue
        findings.append(
            {
                "kind": "missing-cli-flag",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live flag `{flag}` is not documented.",
                "impact": "Users may miss supported behavior or defaults.",
                "patch_direction": f"Document `{flag}` in the canonical usage docs.",
            }
        )

    for key, doc_ref in docs["config_keys"].items():
        if key in config_keys:
            continue
        suggestion = closest_match(key, sorted(config_keys))
        if not suggestion:
            continue
        findings.append(
            {
                "kind": "stale-config-key",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": config_keys[suggestion]["source_ref"],
                "message": f"Documented config key `{key}` does not exist in the live schema.",
                "impact": "Users may set the wrong config key and get ignored behavior.",
                "patch_direction": f"Replace `{key}` with `{suggestion}` in {doc_ref.split(':', 1)[0]}",
            }
        )

    for key, source in config_keys.items():
        if key in docs["config_keys"]:
            continue
        findings.append(
            {
                "kind": "missing-config-key",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live config key `{key}` is not documented.",
                "impact": "Users may not know a supported schema option exists.",
                "patch_direction": f"Document `{key}` in the configuration reference.",
            }
        )

    for ref in interfaces["referenced_paths"]:
        if ref["exists"]:
            continue
        findings.append(
            {
                "kind": "broken-referenced-path",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": ref["doc_ref"],
                "source_ref": "filesystem",
                "message": f"Referenced path `{ref['path']}` does not exist.",
                "impact": "Users may follow a broken path or setup step.",
                "patch_direction": f"Update or remove `{ref['path']}` in {ref['doc_ref'].split(':', 1)[0]}",
            }
        )

    findings.extend(find_private_infra_leaks(root))

    return {
        "repo_root": str(root),
        "scope": "documentation-drift-audit",
        "artifact_map": {
            "doc_surfaces": inventory["doc_surfaces"],
            "public_doc_surfaces": inventory["public_doc_surfaces"],
            "source_truth_candidates": inventory["source_truth_candidates"],
        },
        "findings": findings,
        "direct_evidence_vs_inference": (
            "All findings in this report are grounded in repo files, argparse definitions, "
            "JSON schema files, and filesystem checks."
        ),
        "required_tests_checks": [
            "Run the generated regression check for the highest-risk drift class.",
        ],
        "recommended_actions": [finding["patch_direction"] for finding in findings[:5]],
    }


def build_regression_check(root: Path, kind: str) -> dict[str, Any]:
    failure_kind = "stale-cli-flag" if kind == "cli-flags" else kind
    script_path = Path(__file__).resolve().parent.parent / "documentation_wizard.py"
    command = f'python3 "{script_path}" report --repo "{root}"'
    script = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# generated from documentation_wizard.py report",
            f"report_json=$({command})",
            (
                'echo "$report_json" | python3 -c \'import json,sys; data=json.load(sys.stdin); '
                f'bad=[f for f in data.get("findings", []) if f.get("kind") == "{failure_kind}"]; '
                "raise SystemExit(1 if bad else 0)'"
            ),
        ]
    )
    return {"repo_root": str(root), "kind": kind, "script": script}


regression_check = build_regression_check
