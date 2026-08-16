from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .metadata_parse import metadata_value
from .metadata_registry import read_metadata_texts
from .metadata_yaml import extract_list
from .paths_constants import IGNORED_AUDIT_CHILD_DIRS, IGNORED_PUBLIC_DOC_PARTS, TEXT_SUFFIXES
from .paths_cloud import configured_cloud_home, default_cloud_home
from .paths_public_docs import public_doc_paths
from .paths_scan import iter_repo_files
from .paths_topology import (
    canonical_project_name,
    configured_runtime_home,
    configured_source_home,
    configured_workspace_home,
    normalized_project_slug,
    normalized_repository_slug,
)
from .publish_deny import DEFAULT_PUBLISH_LAYOUT

DEFAULT_PUBLISH_ROOT_NAME = "Analysis"


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
