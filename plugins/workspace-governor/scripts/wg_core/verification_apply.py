from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import _host
from .roots import DEFAULT_BACKUP_ROOT
from .verification_apply_one import apply_one as _apply_one


def apply_one(item: dict[str, Any], backup_root: Path, generation: str) -> dict[str, Any]:
    return _apply_one(item, backup_root, generation, _host.wg())


def _noop_manifest(args: argparse.Namespace, wg: Any) -> dict[str, Any]:
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
        return _noop_manifest(args, wg)

    generated_at = audit_payload.get("generated_at", wg.now_stamp())
    backup_root = Path(args.backup_root or DEFAULT_BACKUP_ROOT).expanduser().resolve() / generated_at
    backup_root.mkdir(parents=True, exist_ok=True)
    results = [
        apply_one(item, backup_root, generated_at) for item in plan if isinstance(item, dict)
    ]
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
