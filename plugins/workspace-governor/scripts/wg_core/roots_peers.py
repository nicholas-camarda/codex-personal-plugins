from __future__ import annotations

import os
from pathlib import Path

from .roots_env import HOME, CURRENT_PLUGIN_ROOT


def peer_plugin_root(plugin_name: str) -> Path:
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


def peer_plugin_script(plugin_name: str, script_name: str) -> Path:
    return peer_plugin_root(plugin_name) / "scripts" / script_name
