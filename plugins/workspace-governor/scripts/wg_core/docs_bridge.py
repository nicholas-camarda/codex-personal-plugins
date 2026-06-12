from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .paths import public_doc_paths
from .roots import DOC_WIZARD_SCRIPT

REFERENCED_PATH_RE = re.compile(r"Referenced path `([^`]+)`")
REMOTE_URL_RE = re.compile(r"https?://|//[A-Za-z0-9.-]+(?:/|$)")
NON_PATH_TOKEN_RE = re.compile(r"^(?:-?(?:\d+(?:\.\d+)?|\.\d+)(?:\^2|%|x)?|e\.g\.?|i\.e\.?)$", re.I)


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


def parse_doc_ref_path(doc_ref: str | None) -> str | None:
    if not doc_ref:
        return None
    return doc_ref.split(":", 1)[0]


def load_doc_ref_line(repo_root: Path, doc_ref: str | None) -> str:
    if not doc_ref or ":" not in doc_ref:
        return ""
    doc_path, line_text = doc_ref.rsplit(":", 1)
    if not line_text.isdigit():
        return ""
    path = repo_root / doc_path
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    line_number = int(line_text)
    if line_number < 1 or line_number > len(lines):
        return ""
    return lines[line_number - 1]


def referenced_path_token(message: str | None) -> str | None:
    if not message:
        return None
    match = REFERENCED_PATH_RE.search(message)
    if not match:
        return None
    return match.group(1)


def filter_doc_findings(repo_root: Path, findings: list[dict[str, Any]], public_docs: set[str]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        doc_ref = finding.get("doc_ref")
        doc_path = parse_doc_ref_path(doc_ref)
        if doc_path is None or doc_path not in public_docs:
            continue
        if finding.get("kind") == "broken-referenced-path":
            source_line = load_doc_ref_line(repo_root, doc_ref)
            if REMOTE_URL_RE.search(source_line):
                continue
            token = referenced_path_token(finding.get("message"))
            if token and NON_PATH_TOKEN_RE.fullmatch(token):
                continue
        marker = (finding.get("kind"), doc_ref, finding.get("message"))
        if marker in seen:
            continue
        seen.add(marker)
        filtered.append(finding)
    return filtered


def filter_sanitize_preview(sanitize_preview: dict[str, Any], public_docs: set[str]) -> dict[str, Any]:
    if not isinstance(sanitize_preview, dict):
        return {"changed_files": 0, "rewrites": [], "write": False}
    rewrites = [
        rewrite
        for rewrite in sanitize_preview.get("rewrites", [])
        if isinstance(rewrite, dict) and (rewrite.get("file") or rewrite.get("path")) in public_docs
    ]
    filtered = dict(sanitize_preview)
    filtered["rewrites"] = rewrites
    filtered["changed_files"] = sum(1 for rewrite in rewrites if rewrite.get("changed", True))
    return filtered


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
