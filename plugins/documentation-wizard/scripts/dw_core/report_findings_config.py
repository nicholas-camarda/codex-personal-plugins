from __future__ import annotations

from typing import Any

from .report_findings_match import closest_match


def config_key_findings(docs: dict[str, dict[str, str]], config_keys: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key, doc_ref in docs["config_keys"].items():
        if key in config_keys:
            continue
        suggestion = closest_match(key, sorted(config_keys))
        if not suggestion:
            continue
        findings.append(
            {
                "kind": "stale-config-key",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": config_keys[suggestion]["source_ref"],
                "message": f"Documented config key `{key}` does not exist in the live schema.",
                "impact": "Users may set the wrong config key and get ignored behavior.",
                "patch_direction": f"Replace `{key}` with `{suggestion}` in {doc_ref.split(':', 1)[0]}",
            }
        )
    for key, source in config_keys.items():
        if key in docs["config_keys"]:
            continue
        findings.append(
            {
                "kind": "missing-config-key",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live config key `{key}` is not documented.",
                "impact": "Users may not know a supported schema option exists.",
                "patch_direction": f"Document `{key}` in the configuration reference.",
            }
        )
    return findings
