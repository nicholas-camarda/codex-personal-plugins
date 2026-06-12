from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .verification_check_git import verify_git_state


def verify_destination_files(item: dict[str, Any], check: dict[str, Any], failures: list[str]) -> None:
    src = Path(item["source"])
    dst = Path(item["destination"])
    backup = Path(item["backup"])
    if not check["destination_exists"]:
        failures.append(f"Missing destination: {dst}")
    if item.get("status") == "moved" and check["source_exists"]:
        failures.append(f"Source still exists after move: {src}")
    if not check["backup_exists"]:
        failures.append(f"Missing backup: {backup}")


def verify_signatures(item: dict[str, Any], check: dict[str, Any], args: Any, wg: Any, failures: list[str]) -> None:
    backup = Path(item["backup"])
    dst = Path(item["destination"])
    if not backup.exists() or not dst.exists():
        return
    check["backup_signature"] = wg.tree_signature(backup, deep=args.deep)
    check["destination_signature"] = wg.tree_signature(dst, deep=args.deep)
    if not wg.signatures_match(check["backup_signature"], check["destination_signature"]):
        failures.append(f"Signature mismatch: {dst}")


def verify_test_command(item: dict[str, Any], check: dict[str, Any], args: Any, failures: list[str]) -> None:
    dst = Path(item["destination"])
    if not args.test_command or not dst.exists():
        return
    proc = subprocess.run(args.test_command, cwd=dst)
    check["test_returncode"] = proc.returncode
    if proc.returncode != 0:
        failures.append(f"Test command failed in {dst}: {args.test_command}")


def verify_item(item: dict[str, Any], args: Any, wg: Any) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if item.get("status") == "failed":
        failures.append(f"Apply step failed for {item.get('source')}: {item.get('failure_reason')}")
        return {"source": item.get("source"), "status": "skipped-apply-failure"}, failures

    src = Path(item["source"])
    dst = Path(item["destination"])
    backup = Path(item["backup"])
    check: dict[str, Any] = {
        "source": str(src),
        "destination": str(dst),
        "backup": str(backup),
        "source_exists": src.exists(),
        "destination_exists": dst.exists(),
        "backup_exists": backup.exists(),
        "status": item.get("status"),
    }
    verify_destination_files(item, check, failures)
    verify_signatures(item, check, args, wg, failures)
    verify_git_state(item, check, wg, failures)
    verify_test_command(item, check, args, failures)
    return check, failures
