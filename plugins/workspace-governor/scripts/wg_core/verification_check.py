from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import _host
from .verification_check_item import verify_item


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
        check, item_failures = verify_item(item, args, wg)
        checks.append(check)
        failures.extend(item_failures)

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
