from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .metadata import extract_list, metadata_value, read_metadata_texts, slugify
from .publish import DEFAULT_PUBLISH_LAYOUT
from .roots import (
    GENERAL_REPO_CLOUD_ROOT,
    RESEARCH_ROOT,
    RUNTIME_ROOT,
    SIDEPROJECTS_ROOT,
)

DEFAULT_PUBLISH_ROOT_NAME = "Analysis"
SAFE_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
TEXT_SUFFIXES = {
    ".py", ".R", ".r", ".qmd", ".ipynb", ".md", ".txt", ".yaml", ".yml",
    ".json", ".toml", ".ini", ".cfg", ".sh",
}
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
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and name.lower() not in IGNORED_AUDIT_CHILD_DIRS
        ]
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
