#!/usr/bin/env python3
"""Refresh personal marketplace metadata for the home plugin workspace."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_HOME_MARKETPLACE_NAME = "local-plugins"
DEFAULT_HOME_MARKETPLACE_TITLE = "Local Plugins"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def plugin_script_name(plugin_name: str) -> str:
    return plugin_name.replace("-", "_") + ".py"


def discover_plugins(source_root: Path) -> list[dict[str, Any]]:
    plugin_parent = source_root / "plugins"
    plugins: list[dict[str, Any]] = []
    for child in sorted(plugin_parent.iterdir(), key=lambda path: path.name):
        manifest_path = child / ".codex-plugin" / "plugin.json"
        if not manifest_path.exists():
            continue
        manifest = load_json(manifest_path)
        name = manifest.get("name")
        if not isinstance(name, str):
            raise ValueError(f"{manifest_path} is missing a plugin name")
        plugins.append(
            {
                "name": name,
                "root": child.resolve(),
                "manifest": manifest,
                "script": (child / "scripts" / plugin_script_name(name)).resolve(),
                "category": manifest.get("interface", {}).get("category", "Productivity"),
            }
        )
    if not plugins:
        raise ValueError(f"No plugins discovered under {plugin_parent}")
    return plugins


def select_plugins(plugins: list[dict[str, Any]], names: list[str] | None) -> list[dict[str, Any]]:
    if not names:
        return plugins
    wanted = set(names)
    selected = [plugin for plugin in plugins if plugin["name"] in wanted]
    missing = sorted(wanted - {plugin["name"] for plugin in selected})
    if missing:
        raise ValueError(f"Unknown plugins requested: {', '.join(missing)}")
    return selected


def build_marketplace_payload(
    *,
    marketplace_name: str,
    marketplace_title: str,
    plugins: list[dict[str, Any]],
    path_builder,
    install_policy: str,
) -> dict[str, Any]:
    entries = []
    for plugin in plugins:
        entries.append(
            {
                "name": plugin["name"],
                "source": {
                    "source": "local",
                    "path": path_builder(plugin),
                },
                "policy": {
                    "installation": install_policy,
                    "authentication": "ON_INSTALL",
                },
                "category": plugin["category"],
            }
        )
    return {
        "name": marketplace_name,
        "interface": {
            "displayName": marketplace_title,
        },
        "plugins": entries,
    }


def expected_home_workspace_root(home_root: Path) -> Path:
    return home_root / ".codex" / "plugins"


def copy_plugin_to_home(plugin: dict[str, Any], install_root: Path, dry_run: bool = False) -> Path:
    destination = install_root / plugin["name"]
    if dry_run:
        return destination
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(plugin["root"], destination)
    return destination


def validate_plugins(plugins: list[dict[str, Any]], home_root: Path, dry_run: bool = False) -> list[dict[str, Any]]:
    if dry_run:
        return [{"plugin": plugin["name"], "skipped": True, "passed": None} for plugin in plugins]

    results = []
    for plugin in plugins:
        env = dict(os.environ)
        env["HOME"] = str(home_root)
        proc = subprocess.run(
            [sys.executable, str(plugin["script"]), "validate"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise ValueError(f"Validation for {plugin['name']} returned a non-object payload")
        results.append(payload)
    return results


def install_plugins(
    *,
    source_root: Path,
    home_root: Path,
    plugin_names: list[str] | None = None,
    home_marketplace_name: str = DEFAULT_HOME_MARKETPLACE_NAME,
    home_marketplace_title: str = DEFAULT_HOME_MARKETPLACE_TITLE,
    run_validate: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    home_root = home_root.expanduser().resolve()
    install_root = expected_home_workspace_root(home_root)
    home_marketplace_path = home_root / ".agents" / "plugins" / "marketplace.json"

    plugins = select_plugins(discover_plugins(source_root), plugin_names)
    for plugin in plugins:
        installed_root = copy_plugin_to_home(plugin, install_root, dry_run=dry_run)
        plugin["installed_root"] = installed_root
        plugin["script"] = (installed_root / "scripts" / plugin_script_name(plugin["name"])).resolve()
    home_marketplace = build_marketplace_payload(
        marketplace_name=home_marketplace_name,
        marketplace_title=home_marketplace_title,
        plugins=plugins,
        path_builder=lambda plugin: f"./.codex/plugins/{plugin['name']}",
        install_policy="INSTALLED_BY_DEFAULT",
    )

    if not dry_run:
        write_json(home_marketplace_path, home_marketplace)

    validation_results = validate_plugins(plugins, home_root, dry_run=dry_run) if run_validate else []
    all_valid = all(result.get("passed") is not False for result in validation_results)

    return {
        "command": "install",
        "status": "ok" if all_valid else "failed",
        "source_root": str(source_root),
        "home_root": str(home_root),
        "workspace_root": str(install_root),
        "home_marketplace_path": str(home_marketplace_path),
        "plugins": [plugin["name"] for plugin in plugins],
        "validation_results": validation_results,
        "restart_required": not dry_run,
        "all_validations_passed": all_valid,
        "dry_run": bool(dry_run),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh personal marketplace metadata for the home plugin workspace.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install",
        help="Refresh ~/.agents/plugins/marketplace.json from the single source tree in ~/.codex/plugins",
    )
    install_parser.add_argument("--source-root", default=str(Path(__file__).resolve().parents[1]))
    install_parser.add_argument("--home", default=str(Path.home()))
    install_parser.add_argument("--plugin", action="append", dest="plugins", default=[])
    install_parser.add_argument("--home-marketplace-name", default=DEFAULT_HOME_MARKETPLACE_NAME)
    install_parser.add_argument("--home-marketplace-title", default=DEFAULT_HOME_MARKETPLACE_TITLE)
    install_parser.add_argument("--skip-validate", action="store_true")
    install_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    payload = install_plugins(
        source_root=Path(args.source_root),
        home_root=Path(args.home),
        plugin_names=args.plugins or None,
        home_marketplace_name=args.home_marketplace_name,
        home_marketplace_title=args.home_marketplace_title,
        run_validate=not args.skip_validate,
        dry_run=bool(args.dry_run),
    )
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
