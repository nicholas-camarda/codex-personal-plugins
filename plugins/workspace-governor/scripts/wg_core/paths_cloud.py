from __future__ import annotations

from pathlib import Path

from .metadata_fields import metadata_value
from .paths_topology import normalized_repository_slug
from .roots import PROJECT_VAULT_ROOT


PROJECT_VAULT_CATEGORY_BY_TYPE = {
    "research": "Research",
    "sideproject": "Personal Projects",
    "personal_project": "Personal Projects",
    "clinical_residency": "Clinical and Residency",
    "product_hardware": "Product and Hardware",
    "life_admin": "Life Admin",
    "archive": "Archive",
}


def default_cloud_home(repo_root: Path, project_type: str | None) -> Path | None:
    slug = normalized_repository_slug(repo_root)
    category = PROJECT_VAULT_CATEGORY_BY_TYPE.get(project_type or "")
    return PROJECT_VAULT_ROOT / category / slug if category else None


def configured_cloud_home(repo_root: Path, project_type: str | None) -> tuple[Path | None, str]:
    explicit, source = metadata_value(repo_root, "cloud_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    explicit, source = metadata_value(repo_root, "project_vault_home")
    if explicit:
        return Path(explicit).expanduser(), source or "analysis_registry"
    return default_cloud_home(repo_root, project_type), "default"
