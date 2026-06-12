from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .docs_filter import filter_doc_findings, filter_sanitize_preview
from .docs_filter_line import load_doc_ref_line, parse_doc_ref_path, referenced_path_token
from .paths import public_doc_paths
from .roots import DOC_WIZARD_SCRIPT


def ensure_dual_doc_contract(repo_root: Path) -> dict[str, Any]:
    readmes = sorted(p.relative_to(repo_root).as_posix() for p in repo_root.glob("README*") if p.is_file())
    agents_path = repo_root / "AGENTS.md"
    public_docs = [path.relative_to(repo_root).as_posix() for path in public_doc_paths(repo_root)]
    return {
        "has_readme": bool(readmes),
        "readmes": readmes,
        "has_agents": agents_path.exists(),
        "agents_path": "AGENTS.md" if agents_path.exists() else None,
        "public_docs": public_docs,
        "passed": bool(readmes) and agents_path.exists(),
    }


def run_doc_wizard(repo_root: Path, command: str, *extra: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(DOC_WIZARD_SCRIPT), command, "--repo", str(repo_root), *extra],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise ValueError("Documentation wizard returned a non-object payload.")
    return payload


def doc_policy_report(repo_root: Path) -> dict[str, Any]:
    report = run_doc_wizard(repo_root, "report")
    public_docs = {path.relative_to(repo_root).as_posix() for path in public_doc_paths(repo_root)}
    findings = filter_doc_findings(repo_root, report.get("findings", []), public_docs)
    sanitize_preview = filter_sanitize_preview(run_doc_wizard(repo_root, "sanitize-public-docs"), public_docs)
    report = dict(report)
    report["artifact_map"] = dict(report.get("artifact_map", {}))
    report["artifact_map"]["doc_surfaces"] = sorted(public_docs)
    report["artifact_map"]["public_doc_surfaces"] = sorted(public_docs)
    report["findings"] = findings
    report["recommended_actions"] = list(
        dict.fromkeys(
            finding.get("patch_direction")
            for finding in findings
            if isinstance(finding, dict) and finding.get("patch_direction")
        )
    )
    private_leaks = [item for item in findings if isinstance(item, dict) and item.get("kind") == "private-infra-leak"]
    return {
        "report": report,
        "sanitize_preview": sanitize_preview,
        "private_infra_findings": private_leaks,
        "requires_rewrite": bool(sanitize_preview.get("changed_files", 0)),
    }
