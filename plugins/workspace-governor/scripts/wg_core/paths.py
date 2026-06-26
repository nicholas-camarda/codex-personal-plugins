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
from .roots import PROJECT_VAULT_ROOT, WORKSPACES_ROOT

DEFAULT_PUBLISH_ROOT_NAME = "Analysis"
PROJECT_VAULT_CATEGORY_BY_TYPE = {
    "research": "Research",
    "sideproject": "Personal Projects",
    "personal_project": "Personal Projects",
    "clinical_residency": "Clinical and Residency",
    "product_hardware": "Product and Hardware",
    "life_admin": "Life Admin",
    "archive": "Archive",
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


def default_cloud_home(repo_root: Path, project_type: str | None) -> Path | None:
    slug = normalized_project_slug(repo_root)
    category = PROJECT_VAULT_CATEGORY_BY_TYPE.get(project_type or "")
    return PROJECT_VAULT_ROOT / category / slug if category else None


def configured_cloud_home(repo_root: Path, project_type: str | None) -> tuple[Path | None, str]:
    explicit, source = metadata_value(repo_root, "cloud_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return default_cloud_home(repo_root, project_type), "default"


def configured_runtime_home(repo_root: Path) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "runtime_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return WORKSPACES_ROOT / normalized_project_slug(repo_root) / "runtime", "default"


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
