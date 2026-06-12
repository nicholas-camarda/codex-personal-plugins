from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()
CURRENT_PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def unique_paths(candidates: list[Path | None]) -> list[Path]:
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


def windows_home_candidates() -> list[Path]:
    candidates: list[Path | None] = [
        env_path("WIN_HOME"),
        env_path("USERPROFILE"),
    ]
    users_root = Path("/mnt/c/Users")
    usernames = [os.environ.get("WIN_USERNAME"), os.environ.get("USERNAME")]
    if users_root.exists():
        for username in usernames:
            if username:
                candidates.append(users_root / username)
        candidates.extend(sorted(path for path in users_root.iterdir() if path.is_dir()))
    return unique_paths(candidates)


def onedrive_candidates() -> list[Path]:
    candidates: list[Path | None] = [HOME / "Library" / "CloudStorage" / "OneDrive-Personal"]
    for root in windows_home_candidates():
        candidates.extend(
            [
                root / "OneDrive - Personal",
                root / "OneDrive-Personal",
                root / "OneDrive",
            ]
        )
    return unique_paths(candidates)


def resolve_root(env_name: str, *candidates: Path) -> Path:
    override = env_path(env_name)
    if override is not None:
        return override
    for candidate in unique_paths(list(candidates)):
        if candidate.exists():
            return candidate
    for candidate in unique_paths(list(candidates)):
        return candidate
    raise RuntimeError(f"No candidates available for {env_name}")
