#!/usr/bin/env python3
"""Helper CLI for documentation-wizard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dw_core.files import (
    DOC_SUFFIXES,
    HIDDEN_DOC_SEGMENTS,
    IGNORED_DIRS,
    NON_PUBLIC_SEGMENTS,
    PRIVATE_DOC_SEGMENTS,
    is_public_doc,
    iter_files,
    public_doc_surfaces,
    read_text,
    relative,
)
from dw_core.interfaces import (
    ARGPARSE_CALL_RE,
    CLICK_OPTION_CALL_RE,
    COMMAND_MODULE_RE,
    DOMAIN_LIKE_RE,
    FILE_LIKE_SUFFIXES,
    FLAG_RE,
    GENERATED_OUTPUT_ROOT_SEGMENTS,
    MARKDOWN_LINK_RE,
    PATH_CONTINUATION_CHARS,
    PATH_TOKEN_RE,
    TYPER_OPTION_IMPORT_RE,
    VERSION_LIKE_RE,
    extract_cli_flags,
    extract_interfaces,
    is_file_like_token,
    is_valid_relative_doc_link,
    locate_line,
    looks_like_dotted_identifier,
    looks_like_generated_output_path,
    looks_like_non_path_token,
    looks_like_template_path,
    normalize_path_token,
    public_cli_surface_paths,
    referenced_path_exists,
    walk_schema,
)
from dw_core.reporting import (
    BACKTICK_RE,
    SUPPORTED_ANALYSIS_REGISTRY_KEYS,
    analysis_registry_review,
    build_regression_check,
    build_report,
    closest_match,
    documented_tokens,
    inventory_docs,
    regression_check,
    top_level_yaml_keys,
)
from dw_core.sanitize import (
    DATE_SEGMENT_RE,
    PRIVATE_INFRA_PATTERNS,
    InfraPattern,
    find_private_infra_leaks,
    portable_public_replacement,
    portable_suffix_after,
    replacement_for_match,
    sanitize_public_docs,
)


PLUGIN_NAME = "documentation-wizard"
PLUGIN_DISPLAY_NAME = "Documentation Wizard"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def marketplace_root(path: Path) -> Path:
    return path.parents[2]


def marketplace_entry_by_name(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any] | None:
    for item in marketplace.get("plugins", []):
        if isinstance(item, dict) and item.get("name") == plugin_name:
            return item
    return None


def marketplace_entry_has_required_metadata(entry: dict[str, Any] | None) -> bool:
    if not isinstance(entry, dict):
        return False
    source = entry.get("source")
    policy = entry.get("policy")
    return (
        isinstance(source, dict)
        and source.get("source") == "local"
        and isinstance(source.get("path"), str)
        and str(source.get("path")).startswith("./")
        and isinstance(policy, dict)
        and isinstance(policy.get("installation"), str)
        and isinstance(policy.get("authentication"), str)
        and isinstance(entry.get("category"), str)
    )


def marketplace_entry_resolves_to(
    entry: dict[str, Any] | None,
    marketplace_path: Path | None,
    target_path: Path,
) -> bool:
    if not isinstance(entry, dict) or marketplace_path is None:
        return False
    source = entry.get("source")
    if not isinstance(source, dict):
        return False
    relative_path = source.get("path")
    if not isinstance(relative_path, str) or not relative_path.startswith("./"):
        return False
    resolved_target = (marketplace_root(marketplace_path) / relative_path[2:]).resolve()
    return resolved_target == target_path.resolve()


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
    top_level_skill = read_text(plugin_root / "skills" / PLUGIN_NAME / "SKILL.md")

    registered_entry = marketplace_entry_by_name(marketplace, PLUGIN_NAME)
    icon_path = plugin_root / manifest["interface"]["composerIcon"].replace("./", "")
    logo_path = plugin_root / manifest["interface"]["logo"].replace("./", "")

    checks = [
        {"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME},
        {"name": "display-name", "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME},
        {"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH},
        {"name": "marketplace-registration", "passed": registered_entry is not None},
        {
            "name": "marketplace-entry-path",
            "passed": marketplace_entry_resolves_to(registered_entry, marketplace_path, expected_plugin_root),
        },
        {"name": "marketplace-entry-metadata", "passed": marketplace_entry_has_required_metadata(registered_entry)},
        {"name": "plugin-root-is-source-or-home-root", "passed": plugin_root.resolve() == expected_plugin_root.resolve()},
        {"name": "plugin-manifest-exists", "passed": manifest_path.exists()},
        {"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)},
        {"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill},
        {"name": "mention-docs", "passed": "@documentation-wizard" in readme_text},
        {"name": "icon-exists", "passed": icon_path.exists()},
        {"name": "logo-exists", "passed": logo_path.exists()},
    ]
    passed = all(check["passed"] for check in checks)
    return {"plugin": PLUGIN_NAME, "passed": passed, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="documentation-wizard helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="List documentation surfaces and source-of-truth candidates")
    inventory_parser.add_argument("--repo", required=True)

    interfaces_parser = subparsers.add_parser("interfaces", help="Extract live CLI flags, config keys, and referenced paths")
    interfaces_parser.add_argument("--repo", required=True)

    report_parser = subparsers.add_parser("report", help="Generate a documentation drift report")
    report_parser.add_argument("--repo", required=True)

    regression_parser = subparsers.add_parser("regression-check", help="Generate a lightweight regression check")
    regression_parser.add_argument("--repo", required=True)
    regression_parser.add_argument("--kind", required=True, choices=["cli-flags", "config-schema", "referenced-paths", "private-infra"])

    sanitize_parser = subparsers.add_parser("sanitize-public-docs", help="Rewrite public docs to remove maintainer-specific infrastructure details")
    sanitize_parser.add_argument("--repo", required=True)
    sanitize_parser.add_argument("--write", action="store_true", help="Apply the sanitized rewrites to disk")

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    args = parser.parse_args()
    if args.command == "validate":
        payload = validate_plugin(Path(__file__).resolve().parent)
    else:
        root = Path(args.repo).expanduser().resolve()
        if args.command == "inventory":
            payload = inventory_docs(root)
        elif args.command == "interfaces":
            payload = extract_interfaces(root)
        elif args.command == "report":
            payload = build_report(root)
        elif args.command == "sanitize-public-docs":
            payload = sanitize_public_docs(root, write=bool(args.write))
        else:
            kind_map = {
                "cli-flags": "cli-flags",
                "config-schema": "stale-config-key",
                "referenced-paths": "broken-referenced-path",
                "private-infra": "private-infra-leak",
            }
            payload = build_regression_check(root, kind_map[args.kind])
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
