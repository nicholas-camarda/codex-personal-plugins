from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .files import iter_files, read_text, relative


FLAG_RE = re.compile(r"--[A-Za-z0-9][A-Za-z0-9_-]*")
ARGPARSE_CALL_RE = re.compile(r"add_argument\((.*?)\)", re.S)
CLICK_OPTION_CALL_RE = re.compile(r"(?:click\.option|typer\.Option)\((.*?)\)", re.S)
TYPER_OPTION_IMPORT_RE = re.compile(r"\bfrom\s+typer\s+import\b|\bimport\s+typer\b")
COMMAND_MODULE_RE = re.compile(r"module=['\"]([^'\"]+)['\"]")


def locate_line(path: Path, token: str) -> int | None:
    for index, line in enumerate(read_text(path).splitlines(), start=1):
        if token in line:
            return index
    return None


def public_cli_surface_paths(root: Path) -> list[Path]:
    cli_modules: set[Path] = set()
    for cli_path in root.glob("src/**/cli.py"):
        text = read_text(cli_path)
        if "CommandSpec(" not in text:
            continue
        cli_modules.add(cli_path.resolve())
        for module_name in COMMAND_MODULE_RE.findall(text):
            module_path = root / "src" / Path(*module_name.split(".")).with_suffix(".py")
            if module_path.exists():
                cli_modules.add(module_path.resolve())
    return sorted(cli_modules)


def extract_cli_flags(path: Path, root: Path) -> list[dict[str, Any]]:
    text = read_text(path)
    results: list[dict[str, Any]] = []
    for call in ARGPARSE_CALL_RE.findall(text):
        for flag in FLAG_RE.findall(call):
            results.append(
                {
                    "flag": flag,
                    "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                }
            )
    for call in CLICK_OPTION_CALL_RE.findall(text):
        for flag in FLAG_RE.findall(call):
            results.append(
                {
                    "flag": flag,
                    "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                }
            )
    if TYPER_OPTION_IMPORT_RE.search(text):
        for call in re.findall(r"(?<!\.)Option\((.*?)\)", text, re.S):
            for flag in FLAG_RE.findall(call):
                results.append(
                    {
                        "flag": flag,
                        "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                    }
                )
    return results
