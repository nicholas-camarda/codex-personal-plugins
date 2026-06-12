from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from .publish_deny import DEFAULT_PUBLISH_LAYOUT
from .publish_map_artifacts import map_run_artifacts
from .publish_map_data import map_data_paths


def detect_latest_run_year(runtime_root: Path) -> int | None:
    runs_dir = runtime_root / "runs"
    if not runs_dir.exists():
        return None
    years: list[int] = []
    for child in runs_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            years.append(int(child.name))
        except ValueError:
            continue
    return max(years) if years else None


def map_publish_candidate(
    rel_path: str,
    publish_layout: str,
    latest_run_year: int | None,
) -> dict[str, str] | None:
    if publish_layout == DEFAULT_PUBLISH_LAYOUT:
        return {"destination_scope": "snapshot", "destination_relative_path": rel_path}

    if publish_layout != "split-data-flat-analysis-v1":
        return {"destination_scope": "snapshot", "destination_relative_path": rel_path}

    path_obj = PurePosixPath(rel_path)
    data_mapping = map_data_paths(path_obj, latest_run_year)
    if data_mapping is not None:
        return data_mapping

    if latest_run_year is None:
        return None

    return map_run_artifacts(path_obj.parts, latest_run_year)


def iter_publish_candidates(
    runtime_root: Path,
    denylist: list[str],
    publish_layout: str = DEFAULT_PUBLISH_LAYOUT,
) -> dict[str, Any]:
    from .publish_deny import path_denied, relative_to_runtime

    files: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if not runtime_root.exists():
        return {
            "runtime_root": str(runtime_root),
            "exists": False,
            "publish_layout": publish_layout,
            "latest_run_year": None,
            "publishable": files,
            "skipped": skipped,
        }

    latest_run_year = detect_latest_run_year(runtime_root)
    for path in sorted(runtime_root.rglob("*")):
        if not path.is_file():
            continue
        rel = relative_to_runtime(path, runtime_root)
        item = {"source_path": str(path), "relative_path": rel, "bytes": path.stat().st_size}
        if path_denied(rel, denylist):
            skipped.append(item)
            continue
        mapped = map_publish_candidate(rel, publish_layout, latest_run_year)
        if mapped is None:
            skipped.append(item)
            continue
        files.append({**item, **mapped})
    return {
        "runtime_root": str(runtime_root),
        "exists": True,
        "publish_layout": publish_layout,
        "latest_run_year": latest_run_year,
        "publishable": files,
        "skipped": skipped,
    }
