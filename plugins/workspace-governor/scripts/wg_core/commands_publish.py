from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from .docs_bridge import run_doc_wizard
from .git_io import write_json
from .paths import now_stamp
from .publish import build_publish_report


def publish_snapshot_dir(cloud_home: Path, publish_root_name: str, snapshot_id: str) -> Path:
    return cloud_home / publish_root_name / snapshot_id


def verify_git_copy(path: Path, expected: dict[str, Any] | None) -> None:
    from . import _host

    if expected is None:
        return
    actual = _host.wg().git_status(path)
    if not actual:
        raise RuntimeError(f"Expected git repository at {path}")
    if actual.get("head") != expected.get("head") or actual.get("porcelain") != expected.get("porcelain"):
        raise RuntimeError(f"Git state mismatch at {path}")


def collect_publish_destination_checks(report: dict[str, Any]) -> dict[str, Any]:
    snapshot_dir = Path(report["snapshot_dir"])
    destination_sources: dict[str, list[str]] = {}
    existing_destinations: list[dict[str, Any]] = []
    planned_destinations: list[dict[str, Any]] = []

    for item in report.get("publish_candidates", {}).get("publishable", []):
        if not isinstance(item, dict):
            continue
        destination_scope = item.get("destination_scope", "snapshot")
        destination_relative_path = item.get("destination_relative_path", item.get("relative_path"))
        if destination_scope == "cloud_home":
            destination_path = Path(report["cloud_home"]) / str(destination_relative_path)
        else:
            destination_path = snapshot_dir / str(destination_relative_path)
        planned = {
            "source_path": item.get("source_path"),
            "destination_path": str(destination_path),
            "destination_scope": destination_scope,
        }
        planned_destinations.append(planned)
        destination_sources.setdefault(str(destination_path), []).append(str(item.get("source_path")))
        if destination_path.exists():
            existing_destinations.append(planned)

    duplicate_destinations = [
        {"destination_path": destination_path, "source_paths": source_paths}
        for destination_path, source_paths in sorted(destination_sources.items())
        if len(source_paths) > 1
    ]
    return {
        "planned_destination_count": len(planned_destinations),
        "existing_destination_count": len(existing_destinations),
        "duplicate_destination_count": len(duplicate_destinations),
        "existing_destinations": existing_destinations,
        "duplicate_destinations": duplicate_destinations,
    }


def publish_preview(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    payload = {
        "command": "publish-preview",
        "status": "ok",
        **report,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload


def publish(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    report = build_publish_report(repo_root, args.snapshot_id)
    if report["project_type"] in {"research", "sideproject"} and not report["doc_contract"]["passed"]:
        payload = {
            "command": "publish",
            "status": "failed",
            **report,
            "error": "Dual-doc contract failed. README and AGENTS.md must both exist before publish.",
        }
        if args.output:
            write_json(Path(args.output), payload)
        return payload

    destination_checks = report.get("publish_destination_checks", {})
    existing_destination_count = destination_checks.get("existing_destination_count", 0)
    duplicate_destination_count = destination_checks.get("duplicate_destination_count", 0)
    if report["snapshot_exists"] or existing_destination_count > 0 or duplicate_destination_count > 0:
        error_parts: list[str] = []
        if report["snapshot_exists"]:
            error_parts.append("Snapshot target already exists.")
        if existing_destination_count > 0:
            error_parts.append("One or more publish destinations already exist and would be overwritten.")
        if duplicate_destination_count > 0:
            error_parts.append("Two or more publishable files resolve to the same destination path.")
        payload = {
            "command": "publish",
            "status": "failed",
            **report,
            "error": " ".join(error_parts),
        }
        if args.output:
            write_json(Path(args.output), payload)
        return payload

    rewrite_result = {"changed_files": 0, "rewrites": [], "write": False}
    if report["requires_doc_review"]:
        rewrite_result = run_doc_wizard(repo_root, "sanitize-public-docs", "--write")
        report = build_publish_report(repo_root, args.snapshot_id)
        if rewrite_result.get("changed_files", 0) > 0 and not args.approve_doc_review:
            payload = {
                "command": "publish",
                "status": "review-required",
                **report,
                "doc_rewrite_result": rewrite_result,
                "error": (
                    "Public docs were auto-rewritten. Review the changes, then rerun publish "
                    "with --approve-doc-review."
                ),
            }
            if args.output:
                write_json(Path(args.output), payload)
            return payload

    snapshot_dir = Path(report["snapshot_dir"])
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    manifest_rows: list[dict[str, Any]] = []
    for item in report["publish_candidates"]["publishable"]:
        source_path = Path(item["source_path"])
        destination_scope = item.get("destination_scope", "snapshot")
        destination_relative_path = item.get("destination_relative_path", item["relative_path"])
        if destination_scope == "cloud_home":
            destination_path = Path(report["cloud_home"]) / destination_relative_path
        else:
            destination_path = snapshot_dir / destination_relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        copied = shutil.copy2(source_path, destination_path)
        manifest_rows.append(
            {
                "source_path": str(source_path),
                "destination_path": str(destination_path),
                "status": "copied" if copied else "copy_failed",
                "bytes": item["bytes"],
            }
        )
    for item in report["publish_candidates"]["skipped"]:
        manifest_rows.append(
            {
                "source_path": item["source_path"],
                "destination_path": None,
                "status": "skipped_not_publishable",
                "bytes": item["bytes"],
            }
        )
    manifest_path = snapshot_dir / "publish_manifest.json"
    manifest = {
        "generated_at": now_stamp(),
        "repo_root": str(repo_root),
        "runtime_root": report["runtime_root"],
        "snapshot_dir": str(snapshot_dir),
        "rows": manifest_rows,
        "summary": {
            "copied": sum(1 for row in manifest_rows if row["status"] == "copied"),
            "skipped": sum(1 for row in manifest_rows if row["status"] == "skipped_not_publishable"),
            "failed": sum(1 for row in manifest_rows if row["status"] == "copy_failed"),
        },
    }
    write_json(manifest_path, manifest)
    payload = {
        "command": "publish",
        "status": "ok",
        **report,
        "doc_rewrite_result": rewrite_result,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }
    if args.output:
        write_json(Path(args.output), payload)
    return payload
