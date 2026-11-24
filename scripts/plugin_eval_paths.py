from __future__ import annotations

import subprocess
from pathlib import Path


def main_checkout_root(repo_root: Path) -> Path:
    """Return the main checkout for repo_root, so a worktree shares the project's one runtime/.

    Outside a Git repository, repo_root itself is the project folder.
    """
    repo_root = repo_root.expanduser().resolve()
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return repo_root
    return Path(completed.stdout.strip()).resolve().parent


def resolve_runtime_root(repo_root: Path, runtime_root: Path | None = None) -> Path:
    """Resolve the runtime root: the project's ignored runtime/ folder unless overridden.

    An override may live outside the repo or under its runtime/ folder, never elsewhere in the repo,
    where generated files could be committed.
    """
    project_root = main_checkout_root(repo_root)
    default_runtime = project_root / "runtime"
    resolved = (runtime_root or default_runtime).expanduser().resolve()
    repo_roots = {project_root, repo_root.expanduser().resolve()}
    inside_repo = any(resolved == root or root in resolved.parents for root in repo_roots)
    inside_runtime = resolved == default_runtime or default_runtime in resolved.parents
    if inside_repo and not inside_runtime:
        raise ValueError(f"runtime root must not be inside the repo except its runtime/ folder: {resolved}")
    return resolved


def plugin_eval_staging_root(repo_root: Path, runtime_root: Path | None = None) -> Path:
    return resolve_runtime_root(repo_root, runtime_root) / "plugin-eval" / "staging"
