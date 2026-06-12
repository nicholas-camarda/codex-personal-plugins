from __future__ import annotations

import os
from pathlib import Path
from typing import Any

HOME = Path.home()
CURRENT_PLUGIN_ROOT = Path(__file__).resolve().parents[2]


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
