#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.plugin_eval_regression import run_plugin_eval


def find_plugin_eval_js() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    cache_root = codex_home / "plugins" / "cache" / "openai-curated" / "plugin-eval"
    matches = sorted(cache_root.glob("*/scripts/plugin-eval.js"))
    if not matches:
        raise FileNotFoundError(f"Plugin Eval executable not found under {cache_root}")
    return matches[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Plugin Eval through a runtime-only staged plugin copy.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("plugin_root", type=Path)
    analyze_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    analyze_parser.add_argument("--runtime-root", type=Path)
    analyze_parser.add_argument("--plugin-eval-js", type=Path)
    args = parser.parse_args()

    plugin_root = args.plugin_root.expanduser().resolve()
    plugin_eval_js = (args.plugin_eval_js or find_plugin_eval_js()).expanduser().resolve()
    if not plugin_eval_js.is_file():
        parser.error(f"Plugin Eval executable does not exist: {plugin_eval_js}")
    try:
        completed = run_plugin_eval(
            plugin_root,
            plugin_eval_js,
            output_format=args.format,
            runtime_root=args.runtime_root,
        )
    except ValueError as exc:
        parser.error(str(exc))
    sys.stdout.write(completed.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
