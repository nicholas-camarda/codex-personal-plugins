from __future__ import annotations

from pathlib import Path
from typing import Any

from .interfaces import extract_interfaces
from .report_findings import broken_path_findings, registry_findings
from .report_findings_cli import cli_flag_findings
from .report_findings_config import config_key_findings
from .report_inventory import documented_tokens, inventory_docs
from .sanitize import find_private_infra_leaks


def build_report(root: Path) -> dict[str, Any]:
    inventory = inventory_docs(root)
    interfaces = extract_interfaces(root)
    docs = documented_tokens(root)

    cli_flags = {item["flag"]: item for item in interfaces["cli_flags"]}
    config_keys = {item["key"]: item for item in interfaces["config_keys"]}
    registry_review = inventory.get("analysis_registry_review") or {}

    findings: list[dict[str, Any]] = []
    findings.extend(registry_findings(registry_review))
    findings.extend(cli_flag_findings(docs, cli_flags))
    findings.extend(config_key_findings(docs, config_keys))
    findings.extend(broken_path_findings(interfaces["referenced_paths"]))
    findings.extend(find_private_infra_leaks(root))

    return {
        "repo_root": str(root),
        "scope": "documentation-drift-audit",
        "artifact_map": {
            "doc_surfaces": inventory["doc_surfaces"],
            "public_doc_surfaces": inventory["public_doc_surfaces"],
            "source_truth_candidates": inventory["source_truth_candidates"],
        },
        "findings": findings,
        "direct_evidence_vs_inference": (
            "All findings in this report are grounded in repo files, argparse definitions, "
            "JSON schema files, and filesystem checks."
        ),
        "required_tests_checks": [
            "Run the generated regression check for the highest-risk drift class.",
        ],
        "recommended_actions": [finding["patch_direction"] for finding in findings[:5]],
    }
