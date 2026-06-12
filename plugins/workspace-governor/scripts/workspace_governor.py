#!/usr/bin/env python3
"""Audit, migrate, and verify workspace moves with backup-first safety."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wg_core import _host
from wg_core.metadata import (
    SUPPORTED_ANALYSIS_REGISTRY_KEYS,
    extract_list,
    extract_scalar,
    infer_project_profile,
    load_text,
    metadata_value,
    parse_metadata_text,
    read_metadata_texts,
    repo_software_signals,
    review_analysis_registry,
    slugify,
    top_level_yaml_keys,
)
from wg_core.planning import build_audit_payload, build_dry_run_plan, classify_candidate
from wg_core.publish import (
    DEFAULT_PUBLISH_LAYOUT,
    GLOBAL_PUBLISH_DENYLIST,
    build_publish_report,
    detect_latest_run_year,
    iter_publish_candidates,
    map_publish_candidate,
    path_denied,
)
from wg_core.roots import (
    DEFAULT_BACKUP_ROOT,
    DOC_WIZARD_SCRIPT,
    GENERAL_REPO_CLOUD_ROOT,
    LEGACY_ROOT,
    ONEDRIVE_ROOT,
    PROJECTS_ROOT,
    RESEARCH_ROOT,
    RUNTIME_ROOT,
    SIDEPROJECTS_ROOT,
    _marketplace_entry_by_name,
    _marketplace_entry_has_required_metadata,
    _marketplace_entry_resolves_to,
)
from wg_core.verification import apply_one, apply_plan, copytree_verified, file_digest, verify_manifest

HOME = Path.home()
PLUGIN_NAME = "workspace-governor"
PLUGIN_DISPLAY_NAME = "Workspace Governor"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME
CURRENT_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLISH_ROOT_NAME = "Analysis"

def _peer_plugin_root(plugin_name: str) -> Path:
    env_key = f"CODEX_{plugin_name.upper().replace('-', '_')}_PLUGIN_ROOT"
    candidate_roots: list[Path] = []

    explicit_root = os.environ.get(env_key)
    if explicit_root:
        candidate_roots.append(Path(explicit_root).expanduser())

    plugins_root = os.environ.get("CODEX_PLUGINS_ROOT")
    if plugins_root:
        candidate_roots.append(Path(plugins_root).expanduser() / plugin_name)

    candidate_roots.extend(
        [
            CURRENT_PLUGIN_ROOT.parent / plugin_name,
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

DEFAULT_SCAN_ROOTS = [LEGACY_ROOT, PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT]
TEXT_SUFFIXES = {".py", ".R", ".r", ".qmd", ".ipynb", ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".sh"}
RUNTIME_NAME_RE = re.compile(r"(runtime|scratch|tmp|temp|cache|intermediate|work)", re.I)
RESEARCH_NAME_RE = re.compile(r"(research|analysis|study|paper|clinical|medical|bio|health|uveal)", re.I)
PATH_RE = re.compile(r"(?:(?:~|/Users/[^'\"\s]+)|(?:[A-Za-z]:\\[^'\"\s]+)|(?:\.\.?/[^'\"\s]+))")
DOMAIN_RE = re.compile(r"Research/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")
SAFE_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
REMOTE_URL_RE = re.compile(r"https?://|//[A-Za-z0-9.-]+(?:/|$)")
REFERENCED_PATH_RE = re.compile(r"Referenced path `([^`]+)`")
NON_PATH_TOKEN_RE = re.compile(r"^(?:-?(?:\d+(?:\.\d+)?|\.\d+)(?:\^2|%|x)?|e\.g\.?|i\.e\.?)$", re.I)
IGNORED_PUBLIC_DOC_PARTS = {
    "archive",
    ".agent-os",
    ".codex",
    "node_modules",
    ".git",
    ".history",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "migration_backups",
}
IGNORED_AUDIT_CHILD_DIRS = {
    "archive",
    ".agent-os",
    ".codex",
    "node_modules",
    ".git",
    ".history",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "migration_backups",
}

def canonical_project_name(text: str) -> str:
    candidate = text.strip()
    if SAFE_PROJECT_NAME_RE.fullmatch(candidate):
        return candidate
    return slugify(candidate)

def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def metadata_list(repo_root: Path, key: str) -> tuple[list[str], str | None]:
    registry_text, agents_text = read_metadata_texts(repo_root)
    registry_values = extract_list(registry_text, key)
    if registry_values:
        return registry_values, "analysis_registry"
    agent_values = extract_list(agents_text, key)
    if agent_values:
        return agent_values, "AGENTS.md"
    return [], None

def normalized_project_slug(repo_root: Path) -> str:
    explicit, _ = metadata_value(repo_root, "project_slug")
    if explicit:
        return canonical_project_name(explicit)
    return canonical_project_name(repo_root.name)

def default_cloud_home(repo_root: Path, project_type: str | None) -> Path:
    slug = normalized_project_slug(repo_root)
    if project_type == "sideproject":
        return SIDEPROJECTS_ROOT / slug
    if project_type == "research":
        return RESEARCH_ROOT / slug
    return GENERAL_REPO_CLOUD_ROOT / slug

def configured_cloud_home(repo_root: Path, project_type: str | None) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "cloud_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return default_cloud_home(repo_root, project_type), "default"

def configured_runtime_home(repo_root: Path) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "runtime_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return RUNTIME_ROOT / normalized_project_slug(repo_root), "default"

def configured_publish_root_name(repo_root: Path) -> tuple[str, str]:
    explicit, source = metadata_value(repo_root, "publish_root_name")
    if explicit:
        return explicit, source or "analysis_registry"
    return DEFAULT_PUBLISH_ROOT_NAME, "default"

def configured_publish_layout(repo_root: Path) -> tuple[str, str]:
    explicit, source = metadata_value(repo_root, "publish_layout")
    if explicit:
        return explicit, source or "analysis_registry"
    return DEFAULT_PUBLISH_LAYOUT, "default"

def project_publish_denylist(repo_root: Path) -> tuple[list[str], str | None]:
    return metadata_list(repo_root, "publish_denylist")

def iter_repo_files(repo_root: Path, suffixes: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_AUDIT_CHILD_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if suffixes is not None and path.suffix.lower() not in suffixes:
                continue
            files.append(path)
    return sorted(files)

def public_doc_paths(repo_root: Path) -> list[Path]:
    docs: list[Path] = []
    for path in iter_repo_files(repo_root, TEXT_SUFFIXES):
        rel_path = path.relative_to(repo_root)
        rel_parts = {part.lower() for part in rel_path.parts}
        if any(part.startswith(".") for part in rel_path.parts[:-1]):
            continue
        if rel_parts & IGNORED_PUBLIC_DOC_PARTS:
            continue
        name = path.name.lower()
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = rel_path.as_posix()
        if rel == "AGENTS.md":
            continue
        if ".local." in name or any(part.lower() in {"internal", "private"} for part in rel_path.parts):
            continue
        if rel.startswith("docs/") or path.name.upper().startswith(("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")):
            docs.append(path)
    return docs

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

def publish_snapshot_dir(cloud_home: Path, publish_root_name: str, snapshot_id: str) -> Path:
    return cloud_home / publish_root_name / snapshot_id

def validate_plugin(root: Path) -> dict[str, Any]:
    plugin_root = root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = read_json(manifest_path)
    source_marketplace_path = plugin_root.parents[1] / ".agents" / "plugins" / "marketplace.json"
    source_checkout = plugin_root.parent.name == "plugins" and source_marketplace_path.exists()
    marketplace_path = source_marketplace_path if source_checkout else HOME_MARKETPLACE_PATH
    marketplace = read_json(marketplace_path) if marketplace_path.exists() else {}
    expected_plugin_root = plugin_root if source_checkout else HOME_PLUGIN_ROOT
    readme_text = load_text(plugin_root / "README.md")
    top_level_skill = load_text(plugin_root / "skills" / PLUGIN_NAME / "SKILL.md")

    registered_entry = _marketplace_entry_by_name(marketplace, PLUGIN_NAME)
    icon_path = plugin_root / manifest["interface"]["composerIcon"].replace("./", "")
    logo_path = plugin_root / manifest["interface"]["logo"].replace("./", "")

    checks = [
        {"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME},
        {"name": "display-name", "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME},
        {"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH},
        {"name": "marketplace-registration", "passed": registered_entry is not None},
        {
            "name": "marketplace-entry-path",
            "passed": _marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        },
        {"name": "marketplace-entry-metadata", "passed": _marketplace_entry_has_required_metadata(registered_entry)},
        {"name": "plugin-root-is-source-or-home-root", "passed": plugin_root.resolve() == expected_plugin_root.resolve()},
        {"name": "plugin-manifest-exists", "passed": manifest_path.exists()},
        {"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)},
        {"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill},
        {
            "name": "autonomous-readonly-flow",
            "passed": "prefer `assess --repo <path>`" in top_level_skill.lower() and "run the full non-mutating assessment before pausing to discuss changes" in top_level_skill.lower(),
        },
        {"name": "mention-docs", "passed": "@workspace-governor" in readme_text},
        {"name": "icon-exists", "passed": icon_path.exists()},
        {"name": "logo-exists", "passed": logo_path.exists()},
    ]
    passed = all(check["passed"] for check in checks)
    return {"plugin": PLUGIN_NAME, "passed": passed, "checks": checks}

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload

def run_git(path: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return proc.stdout.strip()

def git_status(path: Path) -> dict[str, Any] | None:
    top = run_git(path, "rev-parse", "--show-toplevel")
    if not top:
        return None
    porcelain = run_git(path, "status", "--porcelain") or ""
    return {
        "top_level": top,
        "head": run_git(path, "rev-parse", "HEAD"),
        "branch": run_git(path, "branch", "--show-current"),
        "porcelain": porcelain.splitlines(),
        "clean": porcelain == "",
    }

def tree_signature(root: Path, deep: bool = False) -> dict[str, Any]:
    files = []
    dirs = 0
    total_bytes = 0
    digest = hashlib.sha256()

    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if ".git" in path.parts:
            continue
        if path.is_dir():
            dirs += 1
            continue
        if path.is_symlink():
            marker = f"L|{rel}|{os.readlink(path)}"
            digest.update(marker.encode("utf-8"))
            files.append(marker)
            continue
        stat = path.stat()
        total_bytes += stat.st_size
        if deep:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            marker = f"F|{rel}|{stat.st_size}|{stat.st_mode:o}|{file_hash}"
        else:
            marker = f"F|{rel}|{stat.st_size}|{stat.st_mode:o}|{int(stat.st_mtime_ns)}"
        digest.update(marker.encode("utf-8"))
        files.append(marker)
    return {
        "root": str(root),
        "file_count": len(files),
        "dir_count": dirs,
        "total_bytes": total_bytes,
        "digest": digest.hexdigest(),
    }

def signatures_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("file_count", "dir_count", "total_bytes", "digest")
    return all(left.get(key) == right.get(key) for key in keys)

def cleanup_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()

def immediate_root_label(path: Path) -> str:
    resolved = path.expanduser().resolve()
    labeled_roots = [
        ("legacy", LEGACY_ROOT),
        ("runtime", RUNTIME_ROOT),
        ("projects", PROJECTS_ROOT),
        ("research", RESEARCH_ROOT),
        ("sideprojects", SIDEPROJECTS_ROOT),
    ]
    for label, root in labeled_roots:
        try:
            resolved.relative_to(root.expanduser().resolve())
            return label
        except ValueError:
            continue
    return "other"

def child_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".") and path.name.lower() not in IGNORED_AUDIT_CHILD_DIRS
        ],
        key=lambda p: p.name.lower(),
    )

def suggested_destination(repo_name: str, profile: dict[str, Any], classification: dict[str, str] | None = None) -> Path | None:
    slug = canonical_project_name(repo_name)
    if classification:
        if classification["kind"] == "research":
            return RESEARCH_ROOT / slug
        return SIDEPROJECTS_ROOT / slug
    if profile["profile_guess"] == "general":
        return None
    if profile["profile_guess"] == "research":
        return RESEARCH_ROOT / slug
    if profile["profile_guess"] == "sideproject":
        return SIDEPROJECTS_ROOT / slug
    return None

def rewrite_candidates(repo_root: Path, destination: Path | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in iter_repo_files(repo_root, TEXT_SUFFIXES):
        rel_path = path.relative_to(repo_root)
        rel_parts = {part.lower() for part in rel_path.parts}
        if any(part.startswith(".") for part in rel_path.parts[:-1]):
            continue
        if rel_parts & IGNORED_PUBLIC_DOC_PARTS:
            continue
        text = load_text(path, limit=16000)
        if not text:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            for match in PATH_RE.findall(line):
                normalized = match.strip().strip("'\"`,")
                expanded = normalized.replace("~", str(HOME), 1) if normalized.startswith("~") else normalized
                if "Desktop/coding" not in expanded and str(LEGACY_ROOT) not in expanded:
                    continue
                suggestion = str(destination) if destination and slugify(repo_root.name) in expanded else None
                candidates.append(
                    {
                        "file": str(rel_path),
                        "line": index,
                        "current_path": normalized,
                        "reason": "legacy-absolute-path",
                        "suggested_replacement": suggestion,
                    }
                )
    return candidates

def build_dry_run_questions(profile: dict[str, Any], destination: Path | None) -> list[str]:
    questions: list[str] = []
    registry_review = profile["metadata"].get("registry_review") or {}
    if registry_review.get("exists") and not registry_review.get("supported", True):
        questions.append(
            "Should analysis_registry.yaml be rewritten to the supported top-level metadata contract before relying on it?"
        )
    if profile["profile_guess"] == "general":
        questions.append("Should this repo stay in place, or be moved into the managed workspace layout?")
    elif profile["profile_guess"] == "unknown":
        questions.append("Should this repo be treated as Research, SideProjects, or as a general software repo?")
    if profile["has_legacy_paths"]:
        questions.append("Are legacy Desktop/coding paths safe to rewrite after migration?")
    if profile["current_root_kind"] == "legacy" and (
        profile["existing_footprints"].get("runtime")
        or profile["existing_footprints"].get("projects")
        or profile["existing_footprints"].get("sideprojects")
        or profile["existing_footprints"].get("research")
    ):
        questions.append("Which existing local tree is authoritative if there are duplicates?")
    if destination is None:
        if profile["profile_guess"] == "general":
            questions.append("If this repo needs a managed destination, what root should it use?")
        else:
            questions.append("What canonical destination should this project use?")
    questions.append("Which test or smoke command should define migration success?")
    return questions

def parse_classifications(values: list[str]) -> dict[str, dict[str, str]]:
    mappings: dict[str, dict[str, str]] = {}
    for raw in values:
        name, spec = raw.split("=", 1)
        slug = slugify(name)
        if ":" in spec:
            kind, domain = spec.split(":", 1)
        else:
            kind, domain = spec, ""
        normalized = kind.strip().lower()
        if normalized not in {"research", "sideproject"}:
            raise ValueError(f"Invalid classification kind '{normalized}'")
        mappings[slug] = {"kind": normalized, "domain": slugify(domain) if domain else ""}
    return mappings

def parse_repo_kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    normalized = kind.strip().lower()
    if normalized not in {"research", "sideproject", "general"}:
        raise ValueError("Repo kind must be research, sideproject, or general.")
    return normalized

def audit(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(root).expanduser().resolve() for root in (args.roots or [str(root) for root in DEFAULT_SCAN_ROOTS])]
    classifications = parse_classifications(args.classify or [])
    records: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            continue
        for child in child_dirs(root):
            records.append(classify_candidate(child, classifications))

    report = build_audit_payload(roots, classifications, records, now_stamp())
    if args.output:
        write_json(Path(args.output), report)
    return report

def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    classifications = parse_classifications(args.classify or [])
    profile = infer_project_profile(repo_root, repo_root.name)
    if args.kind:
        profile["profile_guess"] = parse_repo_kind(args.kind)
    report = build_dry_run_plan(repo_root, profile, classifications)
    if args.output:
        write_json(Path(args.output), report)
    return report

def assess(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")

    classifications = parse_classifications(args.classify or [])
    profile = infer_project_profile(repo_root, repo_root.name)
    if args.kind:
        profile["profile_guess"] = parse_repo_kind(args.kind)

    dry_run_report = build_dry_run_plan(repo_root, profile, classifications)

    audit_roots = [Path(root).expanduser().resolve() for root in (args.roots or [str(root) for root in DEFAULT_SCAN_ROOTS])]
    audit_report = audit(
        argparse.Namespace(
            roots=[str(root) for root in audit_roots],
            classify=args.classify or [],
            output=None,
        )
    )

    publish_report = build_publish_report(repo_root, args.snapshot_id)
    publish_preview_report = {
        "command": "publish-preview",
        "status": "ok",
        **publish_report,
    }

    repo_slug = normalized_project_slug(repo_root)
    related_audit_records = [
        record
        for record in audit_report["records"]
        if record.get("slug") == repo_slug
        or record.get("source") == str(repo_root)
        or record.get("destination") in {dry_run_report.get("proposed_destination"), dry_run_report.get("proposed_code_root")}
    ]
    workspace_plan = audit_report.get("plan", [])
    workspace_move_count = len(workspace_plan) if isinstance(workspace_plan, list) else 0
    dry_run_rewrite_count = len(dry_run_report.get("rewrite_candidates", []))
    doc_contract_passed = dry_run_report.get("doc_contract", {}).get("passed")
    publish_requires_doc_review = publish_preview_report.get("requires_doc_review")

    if workspace_move_count > 0:
        assessment_outcome = "workspace-moves-planned"
        next_step = "review move plan before apply"
    elif dry_run_rewrite_count > 0:
        assessment_outcome = "rewrite-review-needed"
        next_step = "review rewrite candidates; no workspace apply is needed"
    elif publish_requires_doc_review:
        assessment_outcome = "publish-doc-review-needed"
        next_step = "review public-doc sanitization findings; no workspace apply is needed"
    elif not doc_contract_passed:
        assessment_outcome = "doc-contract-missing"
        next_step = "add missing README or AGENTS.md before publish; no workspace apply is needed"
    else:
        assessment_outcome = "no-migration-work-planned"
        next_step = "no workspace apply is needed"

    payload = {
        "command": "assess",
        "status": "ok",
        "generated_at": now_stamp(),
        "repo_root": str(repo_root),
        "repo_slug": repo_slug,
        "dry_run": dry_run_report,
        "audit": audit_report,
        "related_audit_records": related_audit_records,
        "publish_preview": publish_preview_report,
        "summary": {
            "dry_run_question_count": len(dry_run_report.get("questions", [])),
            "dry_run_rewrite_candidate_count": dry_run_rewrite_count,
            "doc_contract_passed": doc_contract_passed,
            "publish_requires_doc_review": publish_requires_doc_review,
            "publishable_candidate_count": len(publish_preview_report.get("publish_candidates", {}).get("publishable", [])),
            "skipped_publish_candidate_count": len(publish_preview_report.get("publish_candidates", {}).get("skipped", [])),
            "related_workspace_record_count": len(related_audit_records),
            "workspace_move_count": workspace_move_count,
            "apply_recommended": workspace_move_count > 0,
            "assessment_outcome": assessment_outcome,
            "next_step": next_step,
        },
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload

def verify_git_copy(path: Path, expected: dict[str, Any] | None) -> None:
    if expected is None:
        return
    actual = git_status(path)
    if not actual:
        raise RuntimeError(f"Expected git repository at {path}")
    if actual.get("head") != expected.get("head") or actual.get("porcelain") != expected.get("porcelain"):
        raise RuntimeError(f"Git state mismatch at {path}")

def collect_publish_destination_checks(report: dict[str, Any]) -> dict[str, Any]:
    snapshot_dir = Path(report["snapshot_dir"])
    destination_sources: dict[str, list[str]] = {}
    existing_destinations: list[dict[str, Any]] = []
    planned_destinations: list[dict[str, Any]] = []

    for item in report.get("publish_candidates", {}).get("publishable", []):
        if not isinstance(item, dict):
            continue
        destination_scope = item.get("destination_scope", "snapshot")
        destination_relative_path = item.get("destination_relative_path", item.get("relative_path"))
        if destination_scope == "cloud_home":
            destination_path = Path(report["cloud_home"]) / str(destination_relative_path)
        else:
            destination_path = snapshot_dir / str(destination_relative_path)
        planned = {
            "source_path": item.get("source_path"),
            "destination_path": str(destination_path),
            "destination_scope": destination_scope,
        }
        planned_destinations.append(planned)
        destination_sources.setdefault(str(destination_path), []).append(str(item.get("source_path")))
        if destination_path.exists():
            existing_destinations.append(planned)

    duplicate_destinations = [
        {"destination_path": destination_path, "source_paths": source_paths}
        for destination_path, source_paths in sorted(destination_sources.items())
        if len(source_paths) > 1
    ]
    return {
        "planned_destination_count": len(planned_destinations),
        "existing_destination_count": len(existing_destinations),
        "duplicate_destination_count": len(duplicate_destinations),
        "existing_destinations": existing_destinations,
        "duplicate_destinations": duplicate_destinations,
    }

def publish_preview(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    payload = {
        "command": "publish-preview",
        "status": "ok",
        **report,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload

def publish(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    if report["project_type"] in {"research", "sideproject"} and not report["doc_contract"]["passed"]:
        payload = {
            "command": "publish",
            "status": "failed",
            **report,
            "error": "Dual-doc contract failed. README and AGENTS.md must both exist before publish.",
        }
        if args.output:
            write_json(Path(args.output), payload)
        return payload

    destination_checks = report.get("publish_destination_checks", {})
    existing_destination_count = destination_checks.get("existing_destination_count", 0)
    duplicate_destination_count = destination_checks.get("duplicate_destination_count", 0)
    if report["snapshot_exists"] or existing_destination_count > 0 or duplicate_destination_count > 0:
        error_parts: list[str] = []
        if report["snapshot_exists"]:
            error_parts.append("Snapshot target already exists.")
        if existing_destination_count > 0:
            error_parts.append("One or more publish destinations already exist and would be overwritten.")
        if duplicate_destination_count > 0:
            error_parts.append("Two or more publishable files resolve to the same destination path.")
        payload = {
            "command": "publish",
            "status": "failed",
            **report,
            "error": " ".join(error_parts),
        }
        if args.output:
            write_json(Path(args.output), payload)
        return payload

    rewrite_result = {"changed_files": 0, "rewrites": [], "write": False}
    if report["requires_doc_review"]:
        rewrite_result = run_doc_wizard(repo_root, "sanitize-public-docs", "--write")
        report = build_publish_report(repo_root, args.snapshot_id)
        if rewrite_result.get("changed_files", 0) > 0 and not args.approve_doc_review:
            payload = {
                "command": "publish",
                "status": "review-required",
                **report,
                "doc_rewrite_result": rewrite_result,
                "error": "Public docs were auto-rewritten. Review the changes, then rerun publish with --approve-doc-review.",
            }
            if args.output:
                write_json(Path(args.output), payload)
            return payload

    snapshot_dir = Path(report["snapshot_dir"])
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    manifest_rows: list[dict[str, Any]] = []
    for item in report["publish_candidates"]["publishable"]:
        source_path = Path(item["source_path"])
        destination_scope = item.get("destination_scope", "snapshot")
        destination_relative_path = item.get("destination_relative_path", item["relative_path"])
        if destination_scope == "cloud_home":
            destination_path = Path(report["cloud_home"]) / destination_relative_path
        else:
            destination_path = snapshot_dir / destination_relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        copied = shutil.copy2(source_path, destination_path)
        manifest_rows.append(
            {
                "source_path": str(source_path),
                "destination_path": str(destination_path),
                "status": "copied" if copied else "copy_failed",
                "bytes": item["bytes"],
            }
        )
    for item in report["publish_candidates"]["skipped"]:
        manifest_rows.append(
            {
                "source_path": item["source_path"],
                "destination_path": None,
                "status": "skipped_not_publishable",
                "bytes": item["bytes"],
            }
        )
    manifest_path = snapshot_dir / "publish_manifest.json"
    manifest = {
        "generated_at": now_stamp(),
        "repo_root": str(repo_root),
        "runtime_root": report["runtime_root"],
        "snapshot_dir": str(snapshot_dir),
        "rows": manifest_rows,
        "summary": {
            "copied": sum(1 for row in manifest_rows if row["status"] == "copied"),
            "skipped": sum(1 for row in manifest_rows if row["status"] == "skipped_not_publishable"),
            "failed": sum(1 for row in manifest_rows if row["status"] == "copy_failed"),
        },
    }
    write_json(manifest_path, manifest)
    payload = {
        "command": "publish",
        "status": "ok",
        **report,
        "doc_rewrite_result": rewrite_result,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace governor helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess_parser = subparsers.add_parser("assess", help="Run the full non-mutating assessment pass for one repo")
    assess_parser.add_argument("--repo", required=True, help="Path to the repository to assess")
    assess_parser.add_argument("--kind", help="Optional override: research, sideproject, or general")
    assess_parser.add_argument("--classify", action="append", help="Explicit classification, e.g. project=sideproject or project=research")
    assess_parser.add_argument("--roots", nargs="*", help="Roots to scan for workspace-wide planning context; defaults to canonical and legacy roots")
    assess_parser.add_argument("--snapshot-id", default=format(datetime.now().date(), "%Y-%m-%d"), help="Snapshot identifier for the cloud publish folder")
    assess_parser.add_argument("--output", help="Write assessment JSON to this path")

    dry_run_parser = subparsers.add_parser("dry-run", help="Inspect one repo and list the questions needed to migrate it safely")
    dry_run_parser.add_argument("--repo", required=True, help="Path to the repository to inspect")
    dry_run_parser.add_argument("--kind", help="Optional override: research, sideproject, or general")
    dry_run_parser.add_argument("--classify", action="append", help="Explicit classification, e.g. project=sideproject or project=research")
    dry_run_parser.add_argument("--output", help="Write dry-run JSON to this path")

    audit_parser = subparsers.add_parser("audit", help="Inventory roots and build a move plan")
    audit_parser.add_argument("--roots", nargs="*", help="Roots to scan; defaults to the canonical and legacy roots")
    audit_parser.add_argument("--classify", action="append", help="Explicit classification, e.g. project=sideproject or project=research")
    audit_parser.add_argument("--output", help="Write audit JSON to this path")

    apply_parser = subparsers.add_parser("apply", help="Apply a move plan from an audit or assess JSON file")
    apply_parser.add_argument("--audit", required=True, help="Audit or assess JSON produced by the audit or assess command")
    apply_parser.add_argument("--backup-root", help="Backup root directory")
    apply_parser.add_argument("--output", help="Write apply manifest JSON to this path")

    verify_parser = subparsers.add_parser("verify", help="Verify a move manifest")
    verify_parser.add_argument("--manifest", required=True, help="Apply manifest JSON produced by apply")
    verify_parser.add_argument("--deep", action="store_true", help="Use content hashes for verification")
    verify_parser.add_argument("--test-command", nargs=argparse.REMAINDER, help="Optional command to run in each destination after verification metadata checks")
    verify_parser.add_argument("--output", help="Write verification JSON to this path")

    preview_parser = subparsers.add_parser("publish-preview", help="Preview publishable runtime artifacts and doc policy checks")
    preview_parser.add_argument("--repo", required=True, help="Path to the repository to inspect")
    preview_parser.add_argument("--snapshot-id", default=format(datetime.now().date(), "%Y-%m-%d"), help="Snapshot identifier for the cloud publish folder")
    preview_parser.add_argument("--output", help="Write publish preview JSON to this path")

    publish_parser = subparsers.add_parser("publish", help="Publish runtime artifacts into a dated cloud snapshot")
    publish_parser.add_argument("--repo", required=True, help="Path to the repository to publish")
    publish_parser.add_argument("--snapshot-id", default=format(datetime.now().date(), "%Y-%m-%d"), help="Snapshot identifier for the cloud publish folder")
    publish_parser.add_argument("--approve-doc-review", action="store_true", help="Acknowledge review after any auto-rewritten public docs")
    publish_parser.add_argument("--output", help="Write publish JSON to this path")

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    return parser

def command_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "assess":
        return assess(args)
    if args.command == "audit":
        return audit(args)
    if args.command == "dry-run":
        return dry_run(args)
    if args.command == "apply":
        return apply_plan(args)
    if args.command == "publish-preview":
        return publish_preview(args)
    if args.command == "publish":
        return publish(args)
    if args.command == "verify":
        if args.test_command and args.test_command[:1] == ["--"]:
            args.test_command = args.test_command[1:]
        return verify_manifest(args)
    if args.command == "validate":
        return validate_plugin(Path(__file__).resolve().parent)
    raise ValueError(f"Unsupported command: {args.command}")

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = command_payload(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"command": getattr(args, "command", None), "status": "failed", "error": str(exc)}
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        raise SystemExit(1) from exc
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")

_host.bind(sys.modules[__name__])

if __name__ == "__main__":
    main()
