from __future__ import annotations

from typing import Any


def registry_findings(registry_review: dict[str, Any]) -> list[dict[str, Any]]:
    if not registry_review.get("exists") or registry_review.get("supported", True):
        return []
    unsupported = ", ".join(registry_review.get("unsupported_top_level_keys") or [])
    return [
        {
            "kind": "unsupported-analysis-registry-shape",
            "severity": "P1",
            "evidence_basis": "Direct",
            "doc_ref": "analysis_registry.yaml",
            "source_ref": "analysis_registry.yaml",
            "message": f"analysis_registry.yaml uses unsupported top-level keys ({unsupported}).",
            "impact": "Tooling may silently ignore most of the file and leave misleading metadata in place.",
            "patch_direction": (
                "Rewrite analysis_registry.yaml to the supported top-level metadata contract: "
                "project_slug, project_type, domain, cloud_home, runtime_home, publish_root_name, publish_denylist."
            ),
        }
    ]


def broken_path_findings(referenced_paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for ref in referenced_paths:
        if ref["exists"]:
            continue
        findings.append(
            {
                "kind": "broken-referenced-path",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": ref["doc_ref"],
                "source_ref": "filesystem",
                "message": f"Referenced path `{ref['path']}` does not exist.",
                "impact": "Users may follow a broken path or setup step.",
                "patch_direction": f"Update or remove `{ref['path']}` in {ref['doc_ref'].split(':', 1)[0]}",
            }
        )
    return findings
