#!/usr/bin/env python3
"""Audit, migrate, and verify workspace moves with backup-first safety."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wg_core import _host
from wg_core.classify import parse_classifications, parse_repo_kind
from wg_core.cli import build_parser, command_payload
from wg_core.commands_assess import assess
from wg_core.commands_audit import audit, dry_run
from wg_core.commands_publish import (
    collect_publish_destination_checks,
    publish,
    publish_preview,
    publish_snapshot_dir,
    verify_git_copy,
)
from wg_core.destination import (
    build_dry_run_questions,
    child_dirs,
    immediate_root_label,
    rewrite_candidates,
    suggested_destination,
)
from wg_core.docs_bridge import (
    doc_policy_report,
    ensure_dual_doc_contract,
    filter_doc_findings,
    filter_sanitize_preview,
    load_doc_ref_line,
    parse_doc_ref_path,
    referenced_path_token,
    run_doc_wizard,
)
from wg_core.git_io import (
    cleanup_path,
    git_status,
    read_json,
    run_git,
    signatures_match,
    tree_signature,
    write_json,
)
from wg_core.metadata import infer_project_profile, load_text, parse_metadata_text, slugify
from wg_core.paths import (
    canonical_project_name,
    configured_cloud_home,
    configured_publish_layout,
    configured_publish_root_name,
    configured_runtime_home,
    default_cloud_home,
    iter_repo_files,
    metadata_list,
    normalized_project_slug,
    now_stamp,
    project_publish_denylist,
    public_doc_paths,
)
from wg_core.planning import build_audit_payload, build_dry_run_plan, classify_candidate
from wg_core.plugin_validate import validate_plugin
from wg_core.publish import (
    DEFAULT_PUBLISH_LAYOUT,
    GLOBAL_PUBLISH_DENYLIST,
    build_publish_report,
    detect_latest_run_year,
    iter_publish_candidates,
    map_publish_candidate,
    path_denied,
)
from wg_core.roots import CURRENT_PLUGIN_ROOT
from wg_core.verification import apply_one, apply_plan, copytree_verified, file_digest, verify_manifest

HOME = Path.home()


def _peer_plugin_root(plugin_name: str) -> Path:
    env_key = f"CODEX_{plugin_name.upper().replace('-', '_')}_PLUGIN_ROOT"
    candidate_roots: list[Path] = []

    explicit_root = os.environ.get(env_key)
    if explicit_root:
        candidate_roots.append(Path(explicit_root).expanduser())

    plugins_root = os.environ.get("CODEX_PLUGINS_ROOT")
    if plugins_root:
        candidate_roots.append(Path(plugins_root).expanduser() / plugin_name)

    candidate_roots.extend(
        [
            CURRENT_PLUGIN_ROOT.parent / plugin_name,
            HOME / ".codex" / "plugins" / plugin_name,
        ]
    )

    seen: set[str] = set()
    fallback = candidate_roots[-1]
    for candidate in candidate_roots:
        marker = str(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        if candidate.exists():
            return candidate.resolve()
        fallback = candidate
    return fallback


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = command_payload(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"command": getattr(args, "command", None), "status": "failed", "error": str(exc)}
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        raise SystemExit(1) from exc
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


_host.bind(sys.modules[__name__])

if __name__ == "__main__":
    main()
