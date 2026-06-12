from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import _host
from .roots import DEFAULT_BACKUP_ROOT

def copytree_verified(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True, copy_function=shutil.copy2)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_one(item: dict[str, Any], backup_root: Path, generation: str) -> dict[str, Any]:
    wg = _host.wg()
    src = Path(item["source"]).expanduser().resolve()
    dst = Path(item["destination"]).expanduser().resolve()
    result: dict[str, Any] = {
        "source": str(src),
        "destination": str(dst),
        "kind": item.get("reason", "move"),
        "status": "pending",
        "rollback_available": True,
    }

    if not src.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Source does not exist: {src}"
        return result
    if dst.exists():
        result["status"] = "failed"
        result["failure_reason"] = f"Destination already exists: {dst}"
        return result

    pre_git = wg.git_status(src)
    pre_sig = wg.tree_signature(src, deep=True)
    result["pre_signature"] = pre_sig
    result["pre_git"] = pre_git

    backup = backup_root / re.sub(r"[^A-Za-z0-9._-]+", "_", str(src).lstrip(os.sep))
    temp_dst = dst.parent / f".{dst.name}.workspace-governor-{generation}"
    result["backup"] = str(backup)
    result["temp_destination"] = str(temp_dst)

    try:
        if backup.exists():
            raise FileExistsError(f"Backup path already exists: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        copytree_verified(src, backup)

        if temp_dst.exists():
            raise FileExistsError(f"Temporary destination already exists: {temp_dst}")
        temp_dst.parent.mkdir(parents=True, exist_ok=True)
        copytree_verified(src, temp_dst)
        if not wg.signatures_match(wg.tree_signature(temp_dst, deep=True), pre_sig):
            raise RuntimeError(f"Verification failed while staging {src} -> {temp_dst}")
        wg.verify_git_copy(temp_dst, pre_git)

        temp_dst.rename(dst)
        post_sig = wg.tree_signature(dst, deep=True)
        wg.verify_git_copy(dst, pre_git)
        if not wg.signatures_match(post_sig, pre_sig):
            raise RuntimeError(f"Post-move verification failed for {dst}")

        result["post_signature"] = post_sig
        result["post_git"] = wg.git_status(dst)

        try:
            shutil.rmtree(src)
        except Exception as exc:  # noqa: BLE001
            result["status"] = "cleanup-failed"
            result["failure_reason"] = f"Copied to {dst} but could not remove source {src}: {exc}"
            result["source_retained"] = True
            return result

        result["status"] = "moved"
        result["source_retained"] = False
        return result
    except Exception as exc:  # noqa: BLE001
        wg.cleanup_path(temp_dst)
        if dst.exists() and src.exists():
            wg.cleanup_path(dst)
        result["status"] = "failed"
        result["failure_reason"] = str(exc)
        result["source_retained"] = src.exists()
        return result


def apply_plan(args: argparse.Namespace) -> dict[str, Any]:
    wg = _host.wg()
    audit_payload = wg.read_json(Path(args.audit))
    plan_source = "plan"
    if audit_payload.get("command") == "assess":
        nested_audit = audit_payload.get("audit", {})
        if not isinstance(nested_audit, dict):
            raise ValueError("Assess payload has an invalid audit section.")
        audit_payload = nested_audit
        plan_source = "audit.plan"

    plan = audit_payload.get("plan", [])
    if not isinstance(plan, list):
        raise ValueError(f"{plan_source} must be a list.")
    if not plan:
        manifest = {
            "command": "apply",
            "status": "noop",
            "generated_at": wg.now_stamp(),
            "audit": args.audit,
            "backup_root": None,
            "results": [],
            "failures": [],
            "planned_move_count": 0,
            "applied_move_count": 0,
            "skipped_reason": "No planned workspace moves were present in the supplied audit payload.",
        }
        if args.output:
            wg.write_json(Path(args.output), manifest)
        return manifest

    backup_root = Path(args.backup_root or DEFAULT_BACKUP_ROOT).expanduser().resolve() / audit_payload.get("generated_at", wg.now_stamp())
    backup_root.mkdir(parents=True, exist_ok=True)
    results = [apply_one(item, backup_root, audit_payload.get("generated_at", wg.now_stamp())) for item in plan if isinstance(item, dict)]
    failures = [item for item in results if item["status"] in {"failed", "cleanup-failed"}]

    manifest = {
        "command": "apply",
        "status": "ok" if not failures else "failed",
        "generated_at": wg.now_stamp(),
        "audit": args.audit,
        "backup_root": str(backup_root),
        "results": results,
        "failures": failures,
        "planned_move_count": len(plan),
        "applied_move_count": sum(1 for item in results if item.get("status") == "moved"),
    }
    if args.output:
        wg.write_json(Path(args.output), manifest)
    return manifest


def verify_manifest(args: argparse.Namespace) -> dict[str, Any]:
    wg = _host.wg()
    manifest = wg.read_json(Path(args.manifest))
    results = manifest.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Manifest results must be a list.")

    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    for item in results:
        if not isinstance(item, dict):
            continue
        if item.get("status") == "failed":
            failures.append(f"Apply step failed for {item.get('source')}: {item.get('failure_reason')}")
            checks.append({"source": item.get("source"), "status": "skipped-apply-failure"})
            continue
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
        if not check["destination_exists"]:
            failures.append(f"Missing destination: {dst}")
        if item.get("status") == "moved" and check["source_exists"]:
            failures.append(f"Source still exists after move: {src}")
        if not check["backup_exists"]:
            failures.append(f"Missing backup: {backup}")

        if backup.exists() and dst.exists():
            check["backup_signature"] = wg.tree_signature(backup, deep=args.deep)
            check["destination_signature"] = wg.tree_signature(dst, deep=args.deep)
            if not wg.signatures_match(check["backup_signature"], check["destination_signature"]):
                failures.append(f"Signature mismatch: {dst}")

        pre_git = item.get("pre_git")
        if pre_git is not None and dst.exists():
            destination_git = wg.git_status(dst)
            check["destination_git"] = destination_git
            if not destination_git or destination_git.get("head") != pre_git.get("head") or destination_git.get("porcelain") != pre_git.get("porcelain"):
                failures.append(f"Git mismatch after move: {dst}")

        if args.test_command and dst.exists():
            proc = subprocess.run(args.test_command, cwd=dst)
            check["test_returncode"] = proc.returncode
            if proc.returncode != 0:
                failures.append(f"Test command failed in {dst}: {args.test_command}")

        checks.append(check)

    report = {
        "command": "verify",
        "status": "ok" if not failures else "failed",
        "manifest": args.manifest,
        "checked_at": wg.now_stamp(),
        "deep": bool(args.deep),
        "checks": checks,
        "failures": failures,
        "passed": not failures,
    }
    if args.output:
        wg.write_json(Path(args.output), report)
    return report

