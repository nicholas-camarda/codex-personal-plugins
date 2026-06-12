from __future__ import annotations

from pathlib import Path

from .roots_env import HOME, CURRENT_PLUGIN_ROOT, resolve_root, onedrive_candidates
from .roots_marketplace import (
    marketplace_entry_by_name as _marketplace_entry_by_name,
    marketplace_entry_has_required_metadata as _marketplace_entry_has_required_metadata,
    marketplace_entry_resolves_to as _marketplace_entry_resolves_to,
    marketplace_root as _marketplace_root,
)

__all__ = [
    "CURRENT_PLUGIN_ROOT",
    "DEFAULT_BACKUP_ROOT",
    "DEFAULT_SCAN_ROOTS",
    "DOC_WIZARD_SCRIPT",
    "GENERAL_REPO_CLOUD_ROOT",
    "HOME",
    "LEGACY_ROOT",
    "ONEDRIVE_ROOT",
    "PROJECTS_ROOT",
    "RESEARCH_ROOT",
    "RUNTIME_ROOT",
    "SIDEPROJECTS_ROOT",
    "_marketplace_entry_by_name",
    "_marketplace_entry_has_required_metadata",
    "_marketplace_entry_resolves_to",
    "_marketplace_root",
]
from .roots_peers import peer_plugin_script as _peer_plugin_script

ONEDRIVE_ROOT = resolve_root("CODEX_ONEDRIVE_ROOT", *onedrive_candidates())
PROJECTS_ROOT = resolve_root("CODEX_PROJECTS_ROOT", HOME / "Projects")
RUNTIME_ROOT = resolve_root("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")
RESEARCH_ROOT = resolve_root("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")
SIDEPROJECTS_ROOT = resolve_root("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")
GENERAL_REPO_CLOUD_ROOT = resolve_root("CODEX_CLOUD_PROJECTS_ROOT", ONEDRIVE_ROOT / "Projects")
LEGACY_ROOT = resolve_root("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")
DEFAULT_SCAN_ROOTS = [LEGACY_ROOT, PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT]
DEFAULT_BACKUP_ROOT = RUNTIME_ROOT / "workspace-governor" / "backups"
DOC_WIZARD_SCRIPT = _peer_plugin_script("documentation-wizard", "documentation_wizard.py")
