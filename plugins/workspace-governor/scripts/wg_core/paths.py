from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .metadata_parse import metadata_value, slugify
from .metadata_registry import read_metadata_texts
from .metadata_yaml import extract_list
from .paths_constants import IGNORED_AUDIT_CHILD_DIRS, IGNORED_PUBLIC_DOC_PARTS, SAFE_PROJECT_NAME_RE, TEXT_SUFFIXES
from .paths_public_docs import public_doc_paths
from .paths_scan import iter_repo_files
from .publish_deny import DEFAULT_PUBLISH_LAYOUT
from .roots import GENERAL_REPO_CLOUD_ROOT, RESEARCH_ROOT, RUNTIME_ROOT, SIDEPROJECTS_ROOT

DEFAULT_PUBLISH_ROOT_NAME = "Analysis"


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
