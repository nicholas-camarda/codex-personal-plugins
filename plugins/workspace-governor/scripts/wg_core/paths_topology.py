from __future__ import annotations

from pathlib import Path

from .metadata_fields import metadata_value
from .metadata_parse_scalar import slugify
from .paths_constants import SAFE_PROJECT_NAME_RE
from .roots import WORKSPACES_ROOT


def canonical_project_name(text: str) -> str:
    candidate = text.strip()
    if SAFE_PROJECT_NAME_RE.fullmatch(candidate):
        return candidate
    return slugify(candidate)


def normalized_project_slug(repo_root: Path) -> str:
    explicit, _ = metadata_value(repo_root, "project_slug")
    if explicit:
        return canonical_project_name(explicit)
    return canonical_project_name(repo_root.name)


def normalized_repository_slug(repo_root: Path) -> str:
    explicit, _ = metadata_value(repo_root, "repository_slug")
    if explicit:
        return canonical_project_name(explicit)
    return normalized_project_slug(repo_root)


def configured_workspace_home(repo_root: Path) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "workspace_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return WORKSPACES_ROOT / normalized_repository_slug(repo_root), "default"


def configured_source_home(repo_root: Path) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "source_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    workspace_home, workspace_source = configured_workspace_home(repo_root)
    return workspace_home / "source", workspace_source


def configured_runtime_home(repo_root: Path) -> tuple[Path, str]:
    explicit, source = metadata_value(repo_root, "runtime_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    workspace_home, workspace_source = configured_workspace_home(repo_root)
    return workspace_home / "runtime", workspace_source
