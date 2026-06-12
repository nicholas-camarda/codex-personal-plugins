from __future__ import annotations

from pathlib import Path
from typing import Any


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
