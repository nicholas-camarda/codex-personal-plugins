from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli_flags import extract_cli_flags, public_cli_surface_paths
from .files import iter_files, read_text, relative
from .referenced_paths import collect_referenced_paths


def walk_schema(prefix: str, payload: dict[str, Any], sink: list[dict[str, Any]], source_ref: str) -> None:
    for key, spec in (payload.get("properties") or {}).items():
        dotted = f"{prefix}.{key}" if prefix else key
        sink.append(
            {
                "key": dotted,
                "default": spec.get("default"),
                "source_ref": source_ref,
            }
        )
        if isinstance(spec, dict):
            walk_schema(dotted, spec, sink, source_ref)


def collect_schema_config_keys(root: Path) -> list[dict[str, Any]]:
    config_keys: list[dict[str, Any]] = []
    for path in iter_files(root, {".json"}):
        if not path.name.endswith(".schema.json"):
            continue
        source_ref = relative(path, root)
        try:
            payload = json.loads(read_text(path))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            walk_schema("", payload, config_keys, source_ref)
    return config_keys


def extract_interfaces(root: Path) -> dict[str, Any]:
    cli_flags: list[dict[str, Any]] = []
    public_cli_paths = public_cli_surface_paths(root)
    cli_sources = public_cli_paths or list(iter_files(root, {".py"}))
    for path in cli_sources:
        cli_flags.extend(extract_cli_flags(path, root))

    config_keys = collect_schema_config_keys(root)
    referenced_paths = collect_referenced_paths(root)

    return {
        "repo_root": str(root),
        "cli_flags": sorted({item["flag"]: item for item in cli_flags}.values(), key=lambda item: item["flag"]),
        "config_keys": sorted({item["key"]: item for item in config_keys}.values(), key=lambda item: item["key"]),
        "referenced_paths": referenced_paths,
    }
