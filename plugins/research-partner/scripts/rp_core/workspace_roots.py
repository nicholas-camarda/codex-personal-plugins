from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()
ONEDRIVE_ROOT = Path(
    os.environ.get("CODEX_ONEDRIVE_ROOT", HOME / "Library" / "CloudStorage" / "OneDrive-Personal")
).expanduser()
WORKSPACES_ROOT = Path(os.environ.get("CODEX_WORKSPACES_ROOT", HOME / "Workspaces")).expanduser()
PROJECT_VAULT_ROOT = Path(os.environ.get("CODEX_PROJECT_VAULT_ROOT", ONEDRIVE_ROOT / "Project Vault")).expanduser()
RESIDENCY_ROOT = Path(os.environ.get("CODEX_RESIDENCY_ROOT", ONEDRIVE_ROOT / "residency")).expanduser()

PROJECTS_ROOT = Path(os.environ.get("CODEX_PROJECTS_ROOT", HOME / "Projects")).expanduser()
RUNTIME_ROOT = Path(os.environ.get("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")).expanduser()
RESEARCH_ROOT = Path(os.environ.get("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")).expanduser()
SIDEPROJECTS_ROOT = Path(os.environ.get("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")).expanduser()
LEGACY_ROOT = Path(os.environ.get("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")).expanduser()
CANONICAL_ROOTS = (WORKSPACES_ROOT, PROJECT_VAULT_ROOT, RESIDENCY_ROOT)
LEGACY_MIGRATION_ROOTS = (PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT, LEGACY_ROOT)

WORKSPACE_SOURCE_NAME = "workspace-governor dry-run"
