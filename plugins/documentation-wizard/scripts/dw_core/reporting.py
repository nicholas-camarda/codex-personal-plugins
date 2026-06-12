from __future__ import annotations

from pathlib import Path
from typing import Any

from .report_build import build_report
from .report_inventory import BACKTICK_RE, documented_tokens
from .report_inventory_docs import inventory_docs
from .report_registry import SUPPORTED_ANALYSIS_REGISTRY_KEYS, analysis_registry_review, top_level_yaml_keys
from .report_findings_match import closest_match


def build_regression_check(root: Path, kind: str) -> dict[str, Any]:
    failure_kind = "stale-cli-flag" if kind == "cli-flags" else kind
    script_path = Path(__file__).resolve().parent.parent / "documentation_wizard.py"
    command = f'python3 "{script_path}" report --repo "{root}"'
    script = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# generated from documentation_wizard.py report",
            f"report_json=$({command})",
            (
                'echo "$report_json" | python3 -c \'import json,sys; data=json.load(sys.stdin); '
                f'bad=[f for f in data.get("findings", []) if f.get("kind") == "{failure_kind}"]; '
                "raise SystemExit(1 if bad else 0)'"
            ),
        ]
    )
    return {"repo_root": str(root), "kind": kind, "script": script}


regression_check = build_regression_check

__all__ = [
    "BACKTICK_RE",
    "SUPPORTED_ANALYSIS_REGISTRY_KEYS",
    "analysis_registry_review",
    "build_regression_check",
    "build_report",
    "closest_match",
    "documented_tokens",
    "inventory_docs",
    "regression_check",
    "top_level_yaml_keys",
]
