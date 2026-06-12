from __future__ import annotations

from pathlib import Path
from typing import Any


def verify_signatures(item: dict[str, Any], check: dict[str, Any], args: Any, wg: Any, failures: list[str]) -> None:
    backup = Path(item["backup"])
    dst = Path(item["destination"])
    if not backup.exists():
        return
    if not dst.exists():
        return
    check["backup_signature"] = wg.tree_signature(backup, deep=args.deep)
    check["destination_signature"] = wg.tree_signature(dst, deep=args.deep)
    if not wg.signatures_match(check["backup_signature"], check["destination_signature"]):
        failures.append(f"Signature mismatch: {dst}")
