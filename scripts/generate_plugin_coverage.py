from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PLUGINS = [
    "documentation-wizard",
    "research-partner",
    "workspace-governor",
]


def generate_for_plugin(repo_root: Path, plugin_name: str) -> Path:
    source = f"plugins/{plugin_name}/scripts"
    test_dir = f"tests/plugins/{plugin_name}"
    output = repo_root / "plugins" / plugin_name / "coverage.xml"
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
    )
    subprocess.run(
        [sys.executable, "-m", "coverage", "xml", "-o", str(output)],
        cwd=repo_root,
        check=True,
    )
    return output


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    for plugin_name in PLUGINS:
        path = generate_for_plugin(repo_root, plugin_name)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
