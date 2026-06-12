from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from .cli_parsers import build_parser
from .commands_assess import assess
from .commands_audit import audit, dry_run
from .commands_publish import publish, publish_preview
from .plugin_validate import validate_plugin
from .verification import apply_plan, verify_manifest


def _validate_command(_args: argparse.Namespace) -> dict[str, Any]:
    scripts_dir = Path(__file__).resolve().parents[1]
    return validate_plugin(scripts_dir)


def _verify_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.test_command and args.test_command[:1] == ["--"]:
        args.test_command = args.test_command[1:]
    return verify_manifest(args)


_COMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "assess": assess,
    "audit": audit,
    "dry-run": dry_run,
    "apply": apply_plan,
    "publish-preview": publish_preview,
    "publish": publish,
    "verify": _verify_command,
    "validate": _validate_command,
}


def command_payload(args: argparse.Namespace) -> dict[str, Any]:
    handler = _COMMAND_HANDLERS.get(args.command)
    if handler is None:
        raise ValueError(f"Unsupported command: {args.command}")
    return handler(args)
