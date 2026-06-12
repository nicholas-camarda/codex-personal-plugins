from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .git_io import write_json


def publish_failure_payload(
    command: str,
    report: dict[str, Any],
    error: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload = {"command": command, "status": "failed", **report, "error": error}
    if args.output:
        write_json(Path(args.output), payload)
    return payload


def publish_blocked_errors(report: dict[str, Any]) -> str | None:
    destination_checks = report.get("publish_destination_checks", {})
    existing_destination_count = destination_checks.get("existing_destination_count", 0)
    duplicate_destination_count = destination_checks.get("duplicate_destination_count", 0)
    error_parts: list[str] = []
    if report["snapshot_exists"]:
        error_parts.append("Snapshot target already exists.")
    if existing_destination_count > 0:
        error_parts.append("One or more publish destinations already exist and would be overwritten.")
    if duplicate_destination_count > 0:
        error_parts.append("Two or more publishable files resolve to the same destination path.")
    if not error_parts:
        return None
    return " ".join(error_parts)
