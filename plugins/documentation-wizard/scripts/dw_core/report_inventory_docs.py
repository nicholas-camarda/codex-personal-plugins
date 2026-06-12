from __future__ import annotations

from pathlib import Path
from typing import Any

from .files import DOC_SUFFIXES, is_public_doc, iter_files, read_text, relative


def inventory_docs(root: Path) -> dict[str, Any]:
    doc_surfaces = []
    for path in iter_files(root, DOC_SUFFIXES):
        rel = relative(path, root)
        if rel.startswith("docs/") or path.name.upper().startswith(("README", "CHANGELOG", "CONTRIBUTING", "SECURITY")):
            doc_surfaces.append(rel)

    source_truth = []
    for path in iter_files(root, {".py", ".json"}):
        text = read_text(path)
        rel = relative(path, root)
        if "add_argument(" in text:
            source_truth.append({"kind": "cli", "path": rel})
        if path.name.endswith(".schema.json"):
            source_truth.append({"kind": "config-schema", "path": rel})
    if (root / "AGENTS.md").exists():
        source_truth.append({"kind": "ops-metadata", "path": "AGENTS.md"})
    from .report_registry import analysis_registry_review

    registry_review = analysis_registry_review(root)
    if registry_review["exists"] and registry_review["supported"]:
        source_truth.append({"kind": "repo-metadata", "path": "analysis_registry.yaml"})

    return {
        "repo_root": str(root),
        "doc_surfaces": doc_surfaces,
        "public_doc_surfaces": [rel for rel in doc_surfaces if is_public_doc(rel)],
        "source_truth_candidates": source_truth,
        "analysis_registry_review": registry_review,
    }
