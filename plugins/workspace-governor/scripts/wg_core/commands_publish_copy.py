from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .git_io import write_json
from .paths import now_stamp


def copy_publishables(report: dict[str, Any], snapshot_dir: Path) -> list[dict[str, Any]]:
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
    return manifest_rows


def write_publish_manifest(
    repo_root: Path,
    report: dict[str, Any],
    snapshot_dir: Path,
    manifest_rows: list[dict[str, Any]],
) -> tuple[Path, dict[str, Any]]:
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
    return manifest_path, manifest
