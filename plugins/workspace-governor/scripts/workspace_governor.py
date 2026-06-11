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


HOME = Path.home()
PLUGIN_NAME = "workspace-governor"
PLUGIN_DISPLAY_NAME = "Workspace Governor"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME
CURRENT_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_PUBLISH_DENYLIST = [
    ".DS_Store",
    "**/.DS_Store",
    ".env",
    "**/.env",
    "**/.env.*",
    "**/*.log",
    "**/*.tmp",
    "**/*.temp",
    "**/*.cache",
    "**/*.rds",
    "**/*.RData",
    "**/*.Rhistory",
    "**/*.pyc",
    "**/*.pyo",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/logs/**",
    "**/test_output/**",
    "**/tools_output/**",
    "**/tmp/**",
    "**/temp/**",
    "**/cache/**",
    "**/caches/**",
    "**/scratch/**",
    "**/intermediate/**",
    "**/migration_backups/**",
    "**/.git/**",
    "**/*diagnostic*",
    "**/*diagnostics*",
    "**/publish_manifest.json",
]
DEFAULT_PUBLISH_ROOT_NAME = "Analysis"
DEFAULT_PUBLISH_LAYOUT = "mirror-runtime-v1"


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def _unique_paths(candidates: list[Path | None]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        if candidate is None:
            continue
        marker = str(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(candidate)
    return unique


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


def _peer_plugin_script(plugin_name: str, script_name: str) -> Path:
    return _peer_plugin_root(plugin_name) / "scripts" / script_name


def _marketplace_root(path: Path) -> Path:
    return path.parents[2]


def _marketplace_entry_by_name(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any] | None:
    for item in marketplace.get("plugins", []):
        if isinstance(item, dict) and item.get("name") == plugin_name:
            return item
    return None


def _marketplace_entry_has_required_metadata(entry: dict[str, Any] | None) -> bool:
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


def _marketplace_entry_resolves_to(
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
    resolved_target = (_marketplace_root(marketplace_path) / relative_path[2:]).resolve()
    return resolved_target == target_path.resolve()


def _windows_home_candidates() -> list[Path]:
    candidates: list[Path | None] = [
        _env_path("WIN_HOME"),
        _env_path("USERPROFILE"),
    ]
    users_root = Path("/mnt/c/Users")
    usernames = [os.environ.get("WIN_USERNAME"), os.environ.get("USERNAME")]
    if users_root.exists():
        for username in usernames:
            if username:
                candidates.append(users_root / username)
        candidates.extend(sorted(path for path in users_root.iterdir() if path.is_dir()))
    return _unique_paths(candidates)


def _resolve_root(env_name: str, *candidates: Path) -> Path:
    override = _env_path(env_name)
    if override is not None:
        return override
    for candidate in _unique_paths(list(candidates)):
        if candidate.exists():
            return candidate
    for candidate in _unique_paths(list(candidates)):
        return candidate
    raise RuntimeError(f"No candidates available for {env_name}")


def _onedrive_candidates() -> list[Path]:
    candidates: list[Path | None] = [HOME / "Library" / "CloudStorage" / "OneDrive-Personal"]
    for root in _windows_home_candidates():
        candidates.extend(
            [
                root / "OneDrive - Personal",
                root / "OneDrive-Personal",
                root / "OneDrive",
            ]
        )
    return _unique_paths(candidates)


ONEDRIVE_ROOT = _resolve_root("CODEX_ONEDRIVE_ROOT", *_onedrive_candidates())
PROJECTS_ROOT = _resolve_root("CODEX_PROJECTS_ROOT", HOME / "Projects")
RUNTIME_ROOT = _resolve_root("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")
RESEARCH_ROOT = _resolve_root("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")
SIDEPROJECTS_ROOT = _resolve_root("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")
GENERAL_REPO_CLOUD_ROOT = _resolve_root("CODEX_CLOUD_PROJECTS_ROOT", ONEDRIVE_ROOT / "Projects")
LEGACY_ROOT = _resolve_root("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")
DEFAULT_BACKUP_ROOT = RUNTIME_ROOT / "workspace-governor" / "backups"
DOC_WIZARD_SCRIPT = _peer_plugin_script("documentation-wizard", "documentation_wizard.py")

DEFAULT_SCAN_ROOTS = [LEGACY_ROOT, PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT]
TEXT_SUFFIXES = {".py", ".R", ".r", ".qmd", ".ipynb", ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".sh"}
RUNTIME_NAME_RE = re.compile(r"(runtime|scratch|tmp|temp|cache|intermediate|work)", re.I)
RESEARCH_NAME_RE = re.compile(r"(research|analysis|study|paper|clinical|medical|bio|health|uveal)", re.I)
MEDICAL_NAME_RE = re.compile(r"(diabetes|t1dm|endocrin|oncolog|uveal|melanoma|clinical|patient|medical)", re.I)
SIDEPROJECT_NAME_RE = re.compile(r"(bracket|sports|hobby|game|fantasy|bet|mmbayes|ffbayes)", re.I)
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
SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_layout",
    "publish_denylist",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unnamed"


def canonical_project_name(text: str) -> str:
    candidate = text.strip()
    if SAFE_PROJECT_NAME_RE.fullmatch(candidate):
        return candidate
    return slugify(candidate)


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_text(path: Path, limit: int = 64000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def read_metadata_texts(repo_root: Path) -> tuple[str, str]:
    return load_text(repo_root / "analysis_registry.yaml"), load_text(repo_root / "AGENTS.md")


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def review_analysis_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
            "message": None,
        }

    keys = top_level_yaml_keys(load_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    message = None
    if unsupported:
        supported_list = ", ".join(sorted(SUPPORTED_ANALYSIS_REGISTRY_KEYS))
        message = (
            "analysis_registry.yaml contains unsupported top-level keys "
            f"({', '.join(unsupported)}). Supported keys are: {supported_list}."
        )
    return {
        "path": str(path),
        "exists": True,
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
        "message": message,
    }


def extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("'\"`")


def extract_list(text: str, key: str) -> list[str]:
    inline = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$", text)
    if inline:
        values = []
        for item in inline.group(1).split(","):
            normalized = item.strip().strip("'\"`")
            if normalized:
                values.append(normalized)
        return values

    lines = text.splitlines()
    values: list[str] = []
    active = False
    base_indent = 0
    key_pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*$")
    for line in lines:
        if not active:
            match = key_pattern.match(line)
            if not match:
                continue
            active = True
            base_indent = len(match.group(1))
            continue
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip(" "))
        if not stripped:
            continue
        if current_indent <= base_indent and not stripped.startswith("- "):
            break
        bullet_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if bullet_match:
            values.append(bullet_match.group(1).strip().strip("'\"`"))
            continue
        break
    return values


def metadata_value(repo_root: Path, key: str) -> tuple[str | None, str | None]:
    registry_text, agents_text = read_metadata_texts(repo_root)
    registry_value = extract_scalar(registry_text, key)
    if registry_value is not None:
        return registry_value, "analysis_registry"
    agents_value = extract_scalar(agents_text, key)
    if agents_value is not None:
        return agents_value, "AGENTS.md"
    return None, None


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


def repo_software_signals(repo_root: Path) -> list[str]:
    signals: list[str] = []
    file_names = [
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "Makefile",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "tsconfig.json",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "justfile",
    ]
    dir_names = ["src", "tests", "test", "app", "apps", "lib", "pkg", "bin"]

    for name in file_names:
        if (repo_root / name).is_file():
            signals.append(name)
    for name in dir_names:
        if (repo_root / name).is_dir():
            signals.append(f"{name}/")
    return signals


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


def relative_to_runtime(path: Path, runtime_root: Path) -> str:
    return path.relative_to(runtime_root).as_posix()


def path_denied(rel_path: str, denylist: list[str]) -> bool:
    normalized = rel_path.replace(os.sep, "/")
    path_obj = PurePosixPath(normalized)
    for pattern in denylist:
        candidate_patterns = [pattern]
        if pattern.startswith("**/"):
            candidate_patterns.append(pattern[3:])
        for candidate in candidate_patterns:
            if fnmatch.fnmatch(normalized, candidate):
                return True
            if path_obj.match(candidate):
                return True
    return False


def detect_latest_run_year(runtime_root: Path) -> int | None:
    runs_dir = runtime_root / "runs"
    if not runs_dir.exists():
        return None
    years: list[int] = []
    for child in runs_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            years.append(int(child.name))
        except ValueError:
            continue
    return max(years) if years else None


def map_publish_candidate(
    rel_path: str,
    publish_layout: str,
    latest_run_year: int | None,
) -> dict[str, str] | None:
    if publish_layout == DEFAULT_PUBLISH_LAYOUT:
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": rel_path,
        }

    if publish_layout != "split-data-flat-analysis-v1":
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": rel_path,
        }

    path_obj = PurePosixPath(rel_path)
    parts = path_obj.parts

    if parts[:3] == ("data", "raw", "season_datasets") and path_obj.suffix == ".csv":
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts[:2] == ("data", "raw") and len(parts) == 3 and path_obj.suffix == ".json":
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/raw/manifests/{path_obj.stem}_{year_suffix}{path_obj.suffix}"
            ),
        }

    if (
        parts[:3] == ("data", "processed", "combined_datasets")
        and path_obj.name.endswith("season_modern.csv")
    ):
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts[:3] == ("data", "processed", "snake_draft_datasets") and len(parts) >= 4:
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.csv"):
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.csv"
            ),
        }

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.json"):
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.json"
            ),
        }

    if latest_run_year is None:
        return None

    run_prefix = ("runs", str(latest_run_year), "pre_draft")

    if parts[:5] == run_prefix + ("artifacts", "draft_strategy"):
        rest = parts[5:]
        if not rest:
            return None
        relative_rest = PurePosixPath(*rest)
        if relative_rest.match("finalized_drafts/*_test.*"):
            return None
        if relative_rest.name == f"dashboard_payload_{latest_run_year}.json":
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": "dashboard/dashboard_payload.json",
            }
        if relative_rest.name == f"draft_board_{latest_run_year}.html":
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": "dashboard/index.html",
            }
        if relative_rest.name == f"draft_board_{latest_run_year}.json":
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"draft_strategy/{relative_rest.as_posix()}",
        }

    if parts[:5] == run_prefix + ("artifacts", "hybrid_mc_bayesian"):
        rest = PurePosixPath(*parts[5:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"hybrid_mc_bayesian/{rest.as_posix()}",
        }

    if parts[:5] == run_prefix + ("artifacts", "vor_strategy"):
        rest = PurePosixPath(*parts[5:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"vor_strategy/{rest.as_posix()}",
        }

    if parts[:4] == run_prefix + ("diagnostics",):
        rest = PurePosixPath(*parts[4:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"diagnostics/{rest.as_posix()}",
        }

    return None


def collect_publish_candidates(
    runtime_root: Path,
    denylist: list[str],
    publish_layout: str = DEFAULT_PUBLISH_LAYOUT,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if not runtime_root.exists():
        return {
            "runtime_root": str(runtime_root),
            "exists": False,
            "publish_layout": publish_layout,
            "latest_run_year": None,
            "publishable": files,
            "skipped": skipped,
        }

    latest_run_year = detect_latest_run_year(runtime_root)
    for path in sorted(runtime_root.rglob("*")):
        if not path.is_file():
            continue
        rel = relative_to_runtime(path, runtime_root)
        item = {"source_path": str(path), "relative_path": rel, "bytes": path.stat().st_size}
        if path_denied(rel, denylist):
            skipped.append(item)
            continue
        mapped = map_publish_candidate(rel, publish_layout, latest_run_year)
        if mapped is None:
            skipped.append(item)
            continue
        files.append({**item, **mapped})
    return {
        "runtime_root": str(runtime_root),
        "exists": True,
        "publish_layout": publish_layout,
        "latest_run_year": latest_run_year,
        "publishable": files,
        "skipped": skipped,
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


def safe_copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True, copy_function=shutil.copy2)


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


def parse_metadata_text(repo_root: Path) -> dict[str, Any]:
    agents_path = repo_root / "AGENTS.md"
    registry_path = repo_root / "analysis_registry.yaml"
    registry_text, agents_text = read_metadata_texts(repo_root)
    combined = f"{registry_text}\n{agents_text}"
    registry_review = review_analysis_registry(repo_root)
    project_type = None
    domain = None
    cloud_home = None
    signals: list[str] = []

    registry_type = extract_scalar(registry_text, "project_type")
    if registry_type and registry_type.lower() in {"research", "sideproject", "general"}:
        project_type = registry_type.lower()
        signals.append("analysis_registry.project_type")
    else:
        agents_type = extract_scalar(agents_text, "project_type")
        if agents_type and agents_type.lower() in {"research", "sideproject", "general"}:
            project_type = agents_type.lower()
            signals.append("AGENTS.md.project_type")

    registry_domain = extract_scalar(registry_text, "domain")
    if registry_domain:
        domain = slugify(registry_domain)
        signals.append("analysis_registry.domain")
    else:
        agents_domain = extract_scalar(agents_text, "domain")
        if agents_domain:
            domain = slugify(agents_domain)
            signals.append("AGENTS.md.domain")

    cloud_home_value, cloud_home_source = metadata_value(repo_root, "cloud_home")
    if cloud_home_value:
        cloud_home = cloud_home_value
        signals.append(f"{cloud_home_source}.cloud_home")

    if project_type is None and "SideProjects/" in combined:
        project_type = "sideproject"
        signals.append("metadata.sideprojects-path")
    if project_type is None and "Research/" in combined:
        project_type = "research"
        signals.append("metadata.research-path")

    return {
        "agents_path": str(agents_path) if agents_path.exists() else None,
        "registry_path": str(registry_path) if registry_path.exists() else None,
        "project_type": project_type,
        "research_domain": domain,
        "cloud_home": cloud_home,
        "registry_review": registry_review,
        "signals": signals,
    }


def infer_project_profile(repo_root: Path, repo_name: str) -> dict[str, Any]:
    metadata = parse_metadata_text(repo_root)
    software_signals = repo_software_signals(repo_root)
    files = {
        "readmes": sorted(str(p) for p in repo_root.glob("README*")),
        "agents": metadata["agents_path"],
        "registry": metadata["registry_path"],
        "notebooks": sorted(str(p) for p in repo_root.glob("*.ipynb")),
        "r_files": sorted(str(p) for p in repo_root.glob("*.R")),
        "configs": sorted(str(p) for p in repo_root.glob("config.*")),
        "rproj": sorted(str(p) for p in repo_root.glob("*.Rproj")),
    }

    corpus = "\n".join(
        load_text(candidate)
        for candidate in [
            repo_root / "README.md",
            repo_root / "README.txt",
            repo_root / "config.yml",
            repo_root / "config.yaml",
            repo_root / "config.json",
            repo_root / "AGENTS.md",
            repo_root / "analysis_registry.yaml",
        ]
        if candidate.exists()
    ).lower()

    research_terms = ["clinical", "patient", "diabetes", "t1dm", "oncolog", "uveal", "melanoma", "research"]
    sideproject_terms = ["bracket", "sports", "fantasy", "game", "side project"]
    research_content_hits = sum(1 for term in research_terms if term in corpus)
    sideproject_content_hits = sum(1 for term in sideproject_terms if term in corpus)
    research_name_hit = bool(MEDICAL_NAME_RE.search(repo_name))
    sideproject_name_hit = bool(SIDEPROJECT_NAME_RE.search(repo_name))

    research_score = (4 if research_name_hit else 0) + (2 * research_content_hits) + (8 if metadata["project_type"] == "research" else 0)
    sideproject_score = (3 if sideproject_name_hit else 0) + (2 * sideproject_content_hits) + (8 if metadata["project_type"] == "sideproject" else 0)

    existing_cloud_side = SIDEPROJECTS_ROOT / repo_name
    existing_cloud_research = RESEARCH_ROOT / repo_name if (RESEARCH_ROOT / repo_name).exists() else None

    if metadata["project_type"]:
        profile = metadata["project_type"]
        profile_reason = "repo metadata"
    elif existing_cloud_side.exists() and existing_cloud_research is None:
        profile = "sideproject"
        profile_reason = "existing sideprojects footprint"
    elif existing_cloud_research is not None and not existing_cloud_side.exists():
        profile = "research"
        profile_reason = "existing research footprint"
    elif (
        research_score > sideproject_score
        and research_score >= 4
        and (metadata["research_domain"] or research_content_hits >= 2 or (research_name_hit and not software_signals))
    ):
        profile = "research"
        profile_reason = "research domain signals"
    elif (
        sideproject_score > research_score
        and sideproject_score >= 4
        and (sideproject_content_hits >= 2 or (sideproject_name_hit and not software_signals))
    ):
        profile = "sideproject"
        profile_reason = "sideproject signals"
    else:
        profile = "general"
        profile_reason = "standard software-repo signals" if software_signals else "weak domain evidence"

    confidence = 0.18 + min(0.62, abs(research_score - sideproject_score) / 12)
    if profile == "general":
        confidence = 0.35 if software_signals else 0.25
    if metadata["project_type"]:
        confidence = max(confidence, 0.9)
    if metadata["research_domain"]:
        confidence = max(confidence, 0.92)

    return {
        "repo_name": repo_name,
        "files": files,
        "software_signals": software_signals,
        "scores": {"research": research_score, "sideproject": sideproject_score},
        "profile_guess": profile,
        "confidence": round(min(confidence, 0.99), 2),
        "research_domain": metadata["research_domain"],
        "metadata": metadata,
        "existing_footprints": {
            "projects": (PROJECTS_ROOT / repo_name).exists(),
            "runtime": (RUNTIME_ROOT / repo_name).exists(),
            "sideprojects": existing_cloud_side.exists(),
            "research": existing_cloud_research is not None,
            "research_path": str(existing_cloud_research) if existing_cloud_research else None,
        },
        "profile_reason": profile_reason,
        "general_mode": profile == "general",
        "has_legacy_paths": any(
            marker in corpus
            for marker in [
                "desktop/coding",
                "~/desktop/coding",
                str(LEGACY_ROOT).lower(),
                "onedrive-personal/desktop/coding",
                "onedrive - personal/desktop/coding",
            ]
        ),
    }


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


def build_dry_run_plan(repo_root: Path, profile: dict[str, Any], classifications: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    classification = (classifications or {}).get(slugify(repo_root.name))
    destination = suggested_destination(repo_root.name, profile, classification)
    runtime_home, runtime_source = configured_runtime_home(repo_root)
    cloud_home, cloud_source = configured_cloud_home(repo_root, profile["profile_guess"])
    publish_root_name, publish_root_source = configured_publish_root_name(repo_root)
    denylist_overrides, denylist_source = project_publish_denylist(repo_root)
    doc_contract = ensure_dual_doc_contract(repo_root)
    doc_contract_required = profile["profile_guess"] in {"research", "sideproject"}
    if not doc_contract_required:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = False
        doc_contract["passed"] = True
        doc_contract["message"] = "Dual-doc contract is advisory for general software repos."
    else:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = True
    question_profile = dict(profile)
    question_profile["current_root_kind"] = immediate_root_label(repo_root)
    return {
        "command": "dry-run",
        "status": "ok",
        "repo_root": str(repo_root),
        "current_root_kind": immediate_root_label(repo_root),
        "profile_guess": profile["profile_guess"],
        "research_domain": profile.get("research_domain"),
        "confidence": profile["confidence"],
        "profile_reason": profile["profile_reason"],
        "metadata": profile["metadata"],
        "existing_footprints": profile["existing_footprints"],
        "proposed_destination": str(destination) if destination else None,
        "proposed_code_root": str(PROJECTS_ROOT / normalized_project_slug(repo_root)),
        "proposed_runtime_root": str(runtime_home),
        "proposed_cloud_home": str(cloud_home),
        "publish_root_name": publish_root_name,
        "publish_root_source": publish_root_source,
        "runtime_root_source": runtime_source,
        "cloud_home_source": cloud_source,
        "doc_contract": doc_contract,
        "publish_policy": {
            "global_denylist": GLOBAL_PUBLISH_DENYLIST,
            "project_override_denylist": denylist_overrides,
            "override_source": denylist_source,
        },
        "registry_review": profile["metadata"].get("registry_review"),
        "rewrite_candidates": rewrite_candidates(repo_root, destination),
        "questions": build_dry_run_questions(question_profile, destination),
        "signals": profile,
    }


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


def classify_candidate(path: Path, classifications: dict[str, dict[str, str]]) -> dict[str, Any]:
    name = slugify(path.name)
    canonical_name = canonical_project_name(path.name)
    git = git_status(path)
    profile = infer_project_profile(path, path.name) if path.is_dir() else None
    current_root = immediate_root_label(path)
    record: dict[str, Any] = {
        "source": str(path),
        "name": path.name,
        "slug": name,
        "current_root": current_root,
        "git_repo": git is not None,
        "git": git,
        "action": "keep",
        "reason": "already compliant",
        "destination": None,
        "rewrite_candidates": rewrite_candidates(path, None) if path.is_dir() else [],
    }

    if current_root != "legacy":
        return record

    classification = classifications.get(name)
    destination = None
    reason = None
    if classification:
        destination = suggested_destination(path.name, {"profile_guess": classification["kind"], "research_domain": classification["domain"]}, classification)
        reason = f"explicit {classification['kind']} classification"
    elif git is not None:
        destination = PROJECTS_ROOT / canonical_name
        reason = "legacy git repo inferred as general software repo"
    elif RUNTIME_NAME_RE.search(path.name):
        destination = RUNTIME_ROOT / canonical_name
        reason = "legacy runtime/scratch naming"
    elif profile and profile["profile_guess"] in {"research", "sideproject"}:
        destination = suggested_destination(path.name, profile)
        reason = f"repo metadata and heuristics infer {profile['profile_guess']}"

    if destination is None:
        record["action"] = "needs-classification"
        record["reason"] = "ambiguous legacy tree"
        return record

    record["action"] = "move"
    record["reason"] = reason
    record["destination"] = str(destination)
    record["rewrite_candidates"] = rewrite_candidates(path, destination)
    return record


def audit(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(root).expanduser().resolve() for root in (args.roots or [str(root) for root in DEFAULT_SCAN_ROOTS])]
    classifications = parse_classifications(args.classify or [])
    records: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            continue
        for child in child_dirs(root):
            records.append(classify_candidate(child, classifications))

    plan = [record for record in records if record["action"] == "move" and record["destination"]]
    rewrite_plan = [
        {
            "source": record["source"],
            "destination": record["destination"],
            "rewrite_candidates": record["rewrite_candidates"],
        }
        for record in plan
        if record.get("rewrite_candidates")
    ]
    report = {
        "command": "audit",
        "status": "ok",
        "generated_at": now_stamp(),
        "roots": [str(root) for root in roots],
        "classifications": classifications,
        "records": records,
        "plan": plan,
        "skipped": [record for record in records if record["action"] != "move"],
        "rewrite_plan": rewrite_plan,
    }
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


def apply_one(item: dict[str, Any], backup_root: Path, generation: str) -> dict[str, Any]:
    src = Path(item["source"]).expanduser().resolve()
    dst = Path(item["destination"]).expanduser().resolve()
    result: dict[str, Any] = {
        "source": str(src),
        "destination": str(dst),
        "kind": item.get("reason", "move"),
        "status": "pending",
        "rollback_available": True,
    }

    if not src.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Source does not exist: {src}"
        return result
    if dst.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Destination already exists: {dst}"
        return result

    pre_git = git_status(src)
    pre_sig = tree_signature(src, deep=True)
    result["pre_signature"] = pre_sig
    result["pre_git"] = pre_git

    backup = backup_root / re.sub(r"[^A-Za-z0-9._-]+", "_", str(src).lstrip(os.sep))
    temp_dst = dst.parent / f".{dst.name}.workspace-governor-{generation}"
    result["backup"] = str(backup)
    result["temp_destination"] = str(temp_dst)

    try:
        if backup.exists():
            raise FileExistsError(f"Backup path already exists: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        safe_copy_tree(src, backup)

        if temp_dst.exists():
            raise FileExistsError(f"Temporary destination already exists: {temp_dst}")
        temp_dst.parent.mkdir(parents=True, exist_ok=True)
        safe_copy_tree(src, temp_dst)
        if not signatures_match(tree_signature(temp_dst, deep=True), pre_sig):
            raise RuntimeError(f"Verification failed while staging {src} -> {temp_dst}")
        verify_git_copy(temp_dst, pre_git)

        temp_dst.rename(dst)
        post_sig = tree_signature(dst, deep=True)
        verify_git_copy(dst, pre_git)
        if not signatures_match(post_sig, pre_sig):
            raise RuntimeError(f"Post-move verification failed for {dst}")

        result["post_signature"] = post_sig
        result["post_git"] = git_status(dst)

        try:
            shutil.rmtree(src)
        except Exception as exc:  # noqa: BLE001
            result["status"] = "cleanup-failed"
            result["failure_reason"] = f"Copied to {dst} but could not remove source {src}: {exc}"
            result["source_retained"] = True
            return result

        result["status"] = "moved"
        result["source_retained"] = False
        return result
    except Exception as exc:  # noqa: BLE001
        cleanup_path(temp_dst)
        if dst.exists() and src.exists():
            cleanup_path(dst)
        result["status"] = "failed"
        result["failure_reason"] = str(exc)
        result["source_retained"] = src.exists()
        return result


def apply_plan(args: argparse.Namespace) -> dict[str, Any]:
    audit_payload = read_json(Path(args.audit))
    plan_source = "plan"
    if audit_payload.get("command") == "assess":
        nested_audit = audit_payload.get("audit", {})
        if not isinstance(nested_audit, dict):
            raise ValueError("Assess payload has an invalid audit section.")
        audit_payload = nested_audit
        plan_source = "audit.plan"

    plan = audit_payload.get("plan", [])
    if not isinstance(plan, list):
        raise ValueError(f"{plan_source} must be a list.")
    if not plan:
        manifest = {
            "command": "apply",
            "status": "noop",
            "generated_at": now_stamp(),
            "audit": args.audit,
            "backup_root": None,
            "results": [],
            "failures": [],
            "planned_move_count": 0,
            "applied_move_count": 0,
            "skipped_reason": "No planned workspace moves were present in the supplied audit payload.",
        }
        if args.output:
            write_json(Path(args.output), manifest)
        return manifest

    backup_root = Path(args.backup_root or DEFAULT_BACKUP_ROOT).expanduser().resolve() / audit_payload.get("generated_at", now_stamp())
    backup_root.mkdir(parents=True, exist_ok=True)
    results = [apply_one(item, backup_root, audit_payload.get("generated_at", now_stamp())) for item in plan if isinstance(item, dict)]
    failures = [item for item in results if item["status"] in {"failed", "cleanup-failed"}]

    manifest = {
        "command": "apply",
        "status": "ok" if not failures else "failed",
        "generated_at": now_stamp(),
        "audit": args.audit,
        "backup_root": str(backup_root),
        "results": results,
        "failures": failures,
        "planned_move_count": len(plan),
        "applied_move_count": sum(1 for item in results if item.get("status") == "moved"),
    }
    if args.output:
        write_json(Path(args.output), manifest)
    return manifest


def verify_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(Path(args.manifest))
    results = manifest.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Manifest results must be a list.")

    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    for item in results:
        if not isinstance(item, dict):
            continue
        if item.get("status") == "failed":
            failures.append(f"Apply step failed for {item.get('source')}: {item.get('failure_reason')}")
            checks.append({"source": item.get("source"), "status": "skipped-apply-failure"})
            continue
        src = Path(item["source"])
        dst = Path(item["destination"])
        backup = Path(item["backup"])
        check: dict[str, Any] = {
            "source": str(src),
            "destination": str(dst),
            "backup": str(backup),
            "source_exists": src.exists(),
            "destination_exists": dst.exists(),
            "backup_exists": backup.exists(),
            "status": item.get("status"),
        }
        if not check["destination_exists"]:
            failures.append(f"Missing destination: {dst}")
        if item.get("status") == "moved" and check["source_exists"]:
            failures.append(f"Source still exists after move: {src}")
        if not check["backup_exists"]:
            failures.append(f"Missing backup: {backup}")

        if backup.exists() and dst.exists():
            check["backup_signature"] = tree_signature(backup, deep=args.deep)
            check["destination_signature"] = tree_signature(dst, deep=args.deep)
            if not signatures_match(check["backup_signature"], check["destination_signature"]):
                failures.append(f"Signature mismatch: {dst}")

        pre_git = item.get("pre_git")
        if pre_git is not None and dst.exists():
            destination_git = git_status(dst)
            check["destination_git"] = destination_git
            if not destination_git or destination_git.get("head") != pre_git.get("head") or destination_git.get("porcelain") != pre_git.get("porcelain"):
                failures.append(f"Git mismatch after move: {dst}")

        if args.test_command and dst.exists():
            proc = subprocess.run(args.test_command, cwd=dst)
            check["test_returncode"] = proc.returncode
            if proc.returncode != 0:
                failures.append(f"Test command failed in {dst}: {args.test_command}")

        checks.append(check)

    report = {
        "command": "verify",
        "status": "ok" if not failures else "failed",
        "manifest": args.manifest,
        "checked_at": now_stamp(),
        "deep": bool(args.deep),
        "checks": checks,
        "failures": failures,
        "passed": not failures,
    }
    if args.output:
        write_json(Path(args.output), report)
    return report


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


def build_publish_report(repo_root: Path, snapshot_id: str) -> dict[str, Any]:
    profile = infer_project_profile(repo_root, repo_root.name)
    runtime_root, runtime_source = configured_runtime_home(repo_root)
    cloud_home, cloud_source = configured_cloud_home(repo_root, profile["profile_guess"])
    publish_root_name, publish_root_source = configured_publish_root_name(repo_root)
    publish_layout, publish_layout_source = configured_publish_layout(repo_root)
    publish_denylist, denylist_source = project_publish_denylist(repo_root)
    denylist = [*GLOBAL_PUBLISH_DENYLIST, *publish_denylist]
    snapshot_dir = publish_snapshot_dir(cloud_home, publish_root_name, snapshot_id)
    doc_contract = ensure_dual_doc_contract(repo_root)
    doc_policy = doc_policy_report(repo_root)
    doc_contract_required = profile["profile_guess"] in {"research", "sideproject"}
    if not doc_contract_required:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = False
        doc_contract["passed"] = True
        doc_policy = dict(doc_policy)
        doc_policy["requires_rewrite"] = False
    publish_candidates = collect_publish_candidates(runtime_root, denylist, publish_layout)
    report = {
        "repo_root": str(repo_root),
        "project_slug": normalized_project_slug(repo_root),
        "project_type": profile["profile_guess"],
        "registry_review": profile["metadata"].get("registry_review"),
        "doc_contract": doc_contract,
        "doc_policy": doc_policy,
        "runtime_root": str(runtime_root),
        "runtime_root_source": runtime_source,
        "cloud_home": str(cloud_home),
        "cloud_home_source": cloud_source,
        "publish_root_name": publish_root_name,
        "publish_root_source": publish_root_source,
        "publish_layout": publish_layout,
        "publish_layout_source": publish_layout_source,
        "snapshot_id": snapshot_id,
        "snapshot_dir": str(snapshot_dir),
        "snapshot_exists": snapshot_dir.exists(),
        "publish_policy": {
            "global_denylist": GLOBAL_PUBLISH_DENYLIST,
            "project_override_denylist": publish_denylist,
            "override_source": denylist_source,
            "effective_denylist": denylist,
        },
        "publish_candidates": publish_candidates,
    }
    report["requires_doc_review"] = bool(doc_policy.get("requires_rewrite")) and doc_contract_required
    report["publish_destination_checks"] = collect_publish_destination_checks(report)
    return report


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


if __name__ == "__main__":
    main()
