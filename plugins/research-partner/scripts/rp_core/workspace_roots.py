from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()
ONEDRIVE_ROOT = Path(
    os.environ.get("CODEX_ONEDRIVE_ROOT", HOME / "Library" / "CloudStorage" / "OneDrive-Personal")
).expanduser()
PROJECTS_ROOT = Path(os.environ.get("CODEX_PROJECTS_ROOT", HOME / "Projects")).expanduser()
RUNTIME_ROOT = Path(os.environ.get("CODEX_RUNTIME_ROOT", HOME / "ProjectsRuntime")).expanduser()
RESEARCH_ROOT = Path(os.environ.get("CODEX_RESEARCH_ROOT", ONEDRIVE_ROOT / "Research")).expanduser()
SIDEPROJECTS_ROOT = Path(os.environ.get("CODEX_SIDEPROJECTS_ROOT", ONEDRIVE_ROOT / "SideProjects")).expanduser()
LEGACY_ROOT = Path(os.environ.get("CODEX_LEGACY_ROOT", ONEDRIVE_ROOT / "Desktop" / "coding")).expanduser()
CANONICAL_ROOTS = (PROJECTS_ROOT, RUNTIME_ROOT, RESEARCH_ROOT, SIDEPROJECTS_ROOT)

WORKSPACE_SOURCE_NAME = "workspace-governor dry-run"
