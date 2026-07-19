from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from plugin_eval_paths import resolve_runtime_root

PLUGINS = [
    "documentation-wizard",
    "research-partner",
    "workspace-governor",
]


def generate_for_plugin(repo_root: Path, runtime_root: Path | None, plugin_name: str) -> Path:
    runtime_root = resolve_runtime_root(repo_root, runtime_root)
    source = f"plugins/{plugin_name}/scripts"
    test_dir = f"tests/plugins/{plugin_name}"
    output_dir = runtime_root / "plugin-eval" / plugin_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "coverage.xml"
    coverage_env = dict(os.environ)
    coverage_env["COVERAGE_FILE"] = str(output_dir / ".coverage")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            f"--source={source}",
            "-m",
            "unittest",
            "discover",
            "-s",
            test_dir,
        ],
        cwd=repo_root,
        check=True,
        env=coverage_env,
    )
    subprocess.run(
        [sys.executable, "-m", "coverage", "xml", "-o", str(output)],
        cwd=repo_root,
        check=True,
        env=coverage_env,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Plugin Eval coverage in workspace runtime.")
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    try:
        runtime_root = resolve_runtime_root(repo_root, args.runtime_root)
    except ValueError as exc:
        parser.error(str(exc))
    for plugin_name in PLUGINS:
        path = generate_for_plugin(repo_root, runtime_root, plugin_name)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
