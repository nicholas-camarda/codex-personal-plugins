from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bundles import load_json
from .marketplace_checks import (
    marketplace_entry_by_name,
    marketplace_entry_has_required_metadata,
    marketplace_entry_resolves_to,
)
from .peers import peer_plugin_root, peer_plugin_script
from .workspace import read_text

REQUIRED_SKILLS = [
    "assess-literature-support",
    "design-robustness-tests",
    "inspect-analysis-artifacts",
    "research-partner",
    "review-documentation-consistency",
    "review-implementation-validity",
    "review-scientific-interpretation",
    "review-statistical-validity",
    "synthesize-review",
]

PLUGIN_NAME = "research-partner"
PLUGIN_DISPLAY_NAME = "Research Partner"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME


def validate_plugin(root: Path) -> dict[str, Any]:
    plugin_root = root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    source_marketplace_path = plugin_root.parents[1] / ".agents" / "plugins" / "marketplace.json"
    source_checkout = plugin_root.parent.name == "plugins" and source_marketplace_path.exists()
    marketplace_path = source_marketplace_path if source_checkout else HOME_MARKETPLACE_PATH
    marketplace = load_json(marketplace_path) if marketplace_path.exists() else {}
    expected_plugin_root = plugin_root if source_checkout else HOME_PLUGIN_ROOT
    readme_text = read_text(plugin_root / "README.md")
    top_level_skill = read_text(plugin_root / "skills" / "research-partner" / "SKILL.md")
    docs_wizard_skill = peer_plugin_root("documentation-wizard") / "skills" / "documentation-wizard" / "SKILL.md"
    workspace_governor_script = peer_plugin_script("workspace-governor", "workspace_governor.py")

    checks = []

    registered_entry = marketplace_entry_by_name(marketplace, PLUGIN_NAME)
    checks.append({"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME})
    checks.append(
        {
            "name": "display-name",
            "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME,
        }
    )
    checks.append({"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH})
    checks.append({"name": "marketplace-registration", "passed": registered_entry is not None})
    checks.append(
        {
            "name": "marketplace-entry-path",
            "passed": marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        }
    )
    checks.append(
        {
            "name": "marketplace-entry-metadata",
            "passed": marketplace_entry_has_required_metadata(registered_entry),
        }
    )
    checks.append(
        {
            "name": "plugin-root-is-source-or-home-root",
            "passed": plugin_root.resolve() == expected_plugin_root.resolve(),
        }
    )
    checks.append({"name": "plugin-manifest-exists", "passed": manifest_path.exists()})
    checks.append({"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)})
    checks.append({"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill})
    checks.append(
        {
            "name": "default-flow",
            "passed": (
                "review-preflight" in top_level_skill
                and "documentation-wizard" in top_level_skill
                and "review-synthesizer" in top_level_skill
            ),
        }
    )
    checks.append({"name": "mention-docs", "passed": "@research-partner" in readme_text})
    checks.append({"name": "docs-lane-dependency", "passed": docs_wizard_skill.exists()})
    checks.append({"name": "workspace-governor-dependency", "passed": workspace_governor_script.exists()})
    checks.append(
        {
            "name": "workspace-handoff-docs",
            "passed": "workspace-governor" in readme_text and "workspace-governor" in top_level_skill,
        }
    )

    for skill_name in REQUIRED_SKILLS:
        checks.append(
            {
                "name": f"skill:{skill_name}",
                "passed": (plugin_root / "skills" / skill_name / "SKILL.md").exists(),
            }
        )

    composer_icon = manifest.get("interface", {}).get("composerIcon")
    logo = manifest.get("interface", {}).get("logo")
    icon_path = plugin_root / composer_icon.replace("./", "") if isinstance(composer_icon, str) else None
    logo_path = plugin_root / logo.replace("./", "") if isinstance(logo, str) else None
    checks.append({"name": "icon-exists", "passed": icon_path.exists() if icon_path else False})
    checks.append({"name": "logo-exists", "passed": logo_path.exists() if logo_path else False})

    passed = all(check["passed"] for check in checks)
    return {"plugin": "research-partner", "passed": passed, "checks": checks}
