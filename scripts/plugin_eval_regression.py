from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

DECISION_PATTERNS = [
    re.compile(r"\bif\b"),
    re.compile(r"\belif\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\bexcept\b"),
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
]


def plugin_eval_complexity(source: str) -> int:
    return 1 + sum(len(pattern.findall(source)) for pattern in DECISION_PATTERNS)


def analyze_plugin_python(scripts_root: Path) -> dict[str, Any]:
    max_complexity = 0
    long_lines = 0
    per_file: list[dict[str, Any]] = []
    for path in sorted(scripts_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        complexity = plugin_eval_complexity(text)
        file_long_lines = sum(1 for line in text.splitlines() if len(line) > 120)
        max_complexity = max(max_complexity, complexity)
        long_lines += file_long_lines
        per_file.append(
            {
                "path": str(path),
                "complexity": complexity,
                "long_lines": file_long_lines,
            }
        )
    return {
        "max_complexity": max_complexity,
        "long_lines": long_lines,
        "files": per_file,
    }


def run_plugin_eval_json(plugin_root: Path, plugin_eval_js: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["node", str(plugin_eval_js), "analyze", str(plugin_root), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def check_ids(payload: dict[str, Any]) -> set[str]:
    return {check["id"] for check in payload.get("checks", []) if check.get("status") in {"warn", "fail"}}
