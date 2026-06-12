from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def verify_test_command(item: dict[str, Any], check: dict[str, Any], args: Any, failures: list[str]) -> None:
    dst = Path(item["destination"])
    if not args.test_command:
        return
    if not dst.exists():
        return
    proc = subprocess.run(args.test_command, cwd=dst)
    check["test_returncode"] = proc.returncode
    if proc.returncode != 0:
        failures.append(f"Test command failed in {dst}: {args.test_command}")
