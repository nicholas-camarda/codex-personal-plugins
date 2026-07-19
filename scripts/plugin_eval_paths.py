from __future__ import annotations

from pathlib import Path


def resolve_runtime_root(repo_root: Path, runtime_root: Path | None = None) -> Path:
    source_root = repo_root.expanduser().resolve()
    resolved = (runtime_root or source_root.parent / "runtime").expanduser().resolve()
    if resolved == source_root or source_root in resolved.parents:
        raise ValueError(f"runtime root must not be inside source: {resolved}")
    return resolved


def plugin_eval_staging_root(repo_root: Path, runtime_root: Path | None = None) -> Path:
    return resolve_runtime_root(repo_root, runtime_root) / "plugin-eval" / "staging"
