from __future__ import annotations

from typing import Any

from .report_findings_match import closest_match


def cli_flag_findings(docs: dict[str, dict[str, str]], cli_flags: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for flag, doc_ref in docs["flags"].items():
        if flag in cli_flags:
            continue
        suggestion = closest_match(flag, sorted(cli_flags))
        doc_name = doc_ref.split(":", 1)[0]
        patch = (
            f"Replace `{flag}` with `{suggestion}` in {doc_name}"
            if suggestion
            else f"Remove or correct `{flag}` in {doc_name}"
        )
        findings.append(
            {
                "kind": "stale-cli-flag",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": cli_flags.get(suggestion, {}).get("source_ref") if suggestion else "missing-live-flag",
                "message": f"Documented flag `{flag}` does not appear in the live CLI surface.",
                "impact": "Users may copy a command that no longer parses.",
                "patch_direction": patch,
            }
        )
    for flag, source in cli_flags.items():
        if flag in docs["flags"]:
            continue
        findings.append(
            {
                "kind": "missing-cli-flag",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live flag `{flag}` is not documented.",
                "impact": "Users may miss supported behavior or defaults.",
                "patch_direction": f"Document `{flag}` in the canonical usage docs.",
            }
        )
    return findings
