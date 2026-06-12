from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .git_io import read_json
from .metadata_parse import load_text
from .roots_marketplace import (
    marketplace_entry_by_name as _marketplace_entry_by_name,
    marketplace_entry_has_required_metadata as _marketplace_entry_has_required_metadata,
    marketplace_entry_resolves_to as _marketplace_entry_resolves_to,
)

PLUGIN_NAME = "workspace-governor"
PLUGIN_DISPLAY_NAME = "Workspace Governor"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME


def validate_plugin(root: Path) -> dict[str, Any]:
    plugin_root = root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = read_json(manifest_path)
    source_marketplace_path = plugin_root.parents[1] / ".agents" / "plugins" / "marketplace.json"
    source_checkout = plugin_root.parent.name == "plugins" and source_marketplace_path.exists()
    marketplace_path = source_marketplace_path if source_checkout else HOME_MARKETPLACE_PATH
    marketplace = read_json(marketplace_path) if marketplace_path.exists() else {}
    expected_plugin_root = plugin_root if source_checkout else HOME_PLUGIN_ROOT
    readme_text = load_text(plugin_root / "README.md")
    top_level_skill = load_text(plugin_root / "skills" / PLUGIN_NAME / "SKILL.md")

    registered_entry = _marketplace_entry_by_name(marketplace, PLUGIN_NAME)
    icon_path = plugin_root / manifest["interface"]["composerIcon"].replace("./", "")
    logo_path = plugin_root / manifest["interface"]["logo"].replace("./", "")

    checks = [
        {"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME},
        {"name": "display-name", "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME},
        {"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH},
        {"name": "marketplace-registration", "passed": registered_entry is not None},
        {
            "name": "marketplace-entry-path",
            "passed": _marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        },
        {"name": "marketplace-entry-metadata", "passed": _marketplace_entry_has_required_metadata(registered_entry)},
        {
            "name": "plugin-root-is-source-or-home-root",
            "passed": plugin_root.resolve() == expected_plugin_root.resolve(),
        },
        {"name": "plugin-manifest-exists", "passed": manifest_path.exists()},
        {"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)},
        {"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill},
        {
            "name": "autonomous-readonly-flow",
            "passed": (
                "prefer `assess --repo <path>`" in top_level_skill.lower()
                and "run the full non-mutating assessment before pausing to discuss changes"
                in top_level_skill.lower()
            ),
        },
        {"name": "mention-docs", "passed": "@workspace-governor" in readme_text},
        {"name": "icon-exists", "passed": icon_path.exists()},
        {"name": "logo-exists", "passed": logo_path.exists()},
    ]
    passed = all(check["passed"] for check in checks)
    return {"plugin": PLUGIN_NAME, "passed": passed, "checks": checks}
