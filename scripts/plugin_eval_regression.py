from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts.plugin_eval_paths import plugin_eval_staging_root

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


def run_plugin_eval(
    plugin_root: Path,
    plugin_eval_js: Path,
    *,
    output_format: str,
    runtime_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    repo_root = plugin_root.parents[1]
    staging_root = plugin_eval_staging_root(repo_root, runtime_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging_root) as tmpdir:
        staged_root = Path(tmpdir) / plugin_root.name
        shutil.copytree(
            plugin_root,
            staged_root,
            ignore=shutil.ignore_patterns(".coverage", "coverage.xml", "__pycache__"),
        )
        return subprocess.run(
            ["node", str(plugin_eval_js), "analyze", str(staged_root), "--format", output_format],
            check=True,
            capture_output=True,
            text=True,
        )


def run_plugin_eval_json(
    plugin_root: Path,
    plugin_eval_js: Path,
    *,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    completed = run_plugin_eval(
        plugin_root,
        plugin_eval_js,
        output_format="json",
        runtime_root=runtime_root,
    )
    return json.loads(completed.stdout)


def check_ids(payload: dict[str, Any]) -> set[str]:
    return {check["id"] for check in payload.get("checks", []) if check.get("status") in {"warn", "fail"}}
