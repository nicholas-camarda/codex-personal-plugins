from __future__ import annotations


import fnmatch
import os
from pathlib import Path, PurePosixPath
from typing import Any

from . import _host
from .metadata import infer_project_profile

DEFAULT_PUBLISH_LAYOUT = "mirror-runtime-v1"
GLOBAL_PUBLISH_DENYLIST = [
    ".DS_Store",
    "**/.DS_Store",
    ".env",
    "**/.env",
    "**/.env.*",
    "**/*.log",
    "**/*.tmp",
    "**/*.temp",
    "**/*.cache",
    "**/*.rds",
    "**/*.RData",
    "**/*.Rhistory",
    "**/*.pyc",
    "**/*.pyo",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/logs/**",
    "**/test_output/**",
    "**/tools_output/**",
    "**/tmp/**",
    "**/temp/**",
    "**/cache/**",
    "**/caches/**",
    "**/scratch/**",
    "**/intermediate/**",
    "**/migration_backups/**",
    "**/.git/**",
    "**/*diagnostic*",
    "**/*diagnostics*",
    "**/publish_manifest.json",
]

def relative_to_runtime(path: Path, runtime_root: Path) -> str:
    return path.relative_to(runtime_root).as_posix()


def path_denied(rel_path: str, denylist: list[str]) -> bool:
    normalized = rel_path.replace(os.sep, "/")
    path_obj = PurePosixPath(normalized)
    for pattern in denylist:
        candidate_patterns = [pattern]
        if pattern.startswith("**/"):
            candidate_patterns.append(pattern[3:])
        for candidate in candidate_patterns:
            if fnmatch.fnmatch(normalized, candidate):
                return True
            if path_obj.match(candidate):
                return True
    return False


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
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": rel_path,
        }

    if publish_layout != "split-data-flat-analysis-v1":
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": rel_path,
        }

    path_obj = PurePosixPath(rel_path)
    parts = path_obj.parts

    if parts[:3] == ("data", "raw", "season_datasets") and path_obj.suffix == ".csv":
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts[:2] == ("data", "raw") and len(parts) == 3 and path_obj.suffix == ".json":
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/raw/manifests/{path_obj.stem}_{year_suffix}{path_obj.suffix}"
            ),
        }

    if (
        parts[:3] == ("data", "processed", "combined_datasets")
        and path_obj.name.endswith("season_modern.csv")
    ):
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts[:3] == ("data", "processed", "snake_draft_datasets") and len(parts) >= 4:
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": rel_path,
        }

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.csv"):
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.csv"
            ),
        }

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.json"):
        year_suffix = str(latest_run_year) if latest_run_year is not None else "current"
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.json"
            ),
        }

    if latest_run_year is None:
        return None

    run_prefix = ("runs", str(latest_run_year), "pre_draft")

    if parts[:5] == run_prefix + ("artifacts", "draft_strategy"):
        rest = parts[5:]
        if not rest:
            return None
        relative_rest = PurePosixPath(*rest)
        if relative_rest.match("finalized_drafts/*_test.*"):
            return None
        if relative_rest.name == f"dashboard_payload_{latest_run_year}.json":
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": "dashboard/dashboard_payload.json",
            }
        if relative_rest.name == f"draft_board_{latest_run_year}.html":
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": "dashboard/index.html",
            }
        if relative_rest.name == f"draft_board_{latest_run_year}.json":
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"draft_strategy/{relative_rest.as_posix()}",
        }

    if parts[:5] == run_prefix + ("artifacts", "hybrid_mc_bayesian"):
        rest = PurePosixPath(*parts[5:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"hybrid_mc_bayesian/{rest.as_posix()}",
        }

    if parts[:5] == run_prefix + ("artifacts", "vor_strategy"):
        rest = PurePosixPath(*parts[5:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"vor_strategy/{rest.as_posix()}",
        }

    if parts[:4] == run_prefix + ("diagnostics",):
        rest = PurePosixPath(*parts[4:])
        if not rest.parts:
            return None
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"diagnostics/{rest.as_posix()}",
        }

    return None


def iter_publish_candidates(
    runtime_root: Path,
    denylist: list[str],
    publish_layout: str = DEFAULT_PUBLISH_LAYOUT,
) -> dict[str, Any]:
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


def build_publish_report(repo_root: Path, snapshot_id: str) -> dict[str, Any]:
    wg = _host.wg()
    profile = infer_project_profile(repo_root, repo_root.name)
    runtime_root, runtime_source = wg.configured_runtime_home(repo_root)
    cloud_home, cloud_source = wg.configured_cloud_home(repo_root, profile["profile_guess"])
    publish_root_name, publish_root_source = wg.configured_publish_root_name(repo_root)
    publish_layout, publish_layout_source = wg.configured_publish_layout(repo_root)
    publish_denylist, denylist_source = wg.project_publish_denylist(repo_root)
    denylist = [*GLOBAL_PUBLISH_DENYLIST, *publish_denylist]
    snapshot_dir = wg.publish_snapshot_dir(cloud_home, publish_root_name, snapshot_id)
    doc_contract = wg.ensure_dual_doc_contract(repo_root)
    doc_policy = wg.doc_policy_report(repo_root)
    doc_contract_required = profile["profile_guess"] in {"research", "sideproject"}
    if not doc_contract_required:
        doc_contract = dict(doc_contract)
        doc_contract["required"] = False
        doc_contract["passed"] = True
        doc_policy = dict(doc_policy)
        doc_policy["requires_rewrite"] = False
    publish_candidates = iter_publish_candidates(runtime_root, denylist, publish_layout)
    report = {
        "repo_root": str(repo_root),
        "project_slug": wg.normalized_project_slug(repo_root),
        "project_type": profile["profile_guess"],
        "registry_review": profile["metadata"].get("registry_review"),
        "doc_contract": doc_contract,
        "doc_policy": doc_policy,
        "runtime_root": str(runtime_root),
        "runtime_root_source": runtime_source,
        "cloud_home": str(cloud_home),
        "cloud_home_source": cloud_source,
        "publish_root_name": publish_root_name,
        "publish_root_source": publish_root_source,
        "publish_layout": publish_layout,
        "publish_layout_source": publish_layout_source,
        "snapshot_id": snapshot_id,
        "snapshot_dir": str(snapshot_dir),
        "snapshot_exists": snapshot_dir.exists(),
        "publish_policy": {
            "global_denylist": GLOBAL_PUBLISH_DENYLIST,
            "project_override_denylist": publish_denylist,
            "override_source": denylist_source,
            "effective_denylist": denylist,
        },
        "publish_candidates": publish_candidates,
    }
    report["requires_doc_review"] = bool(doc_policy.get("requires_rewrite")) and doc_contract_required
    report["publish_destination_checks"] = wg.collect_publish_destination_checks(report)
    return report

