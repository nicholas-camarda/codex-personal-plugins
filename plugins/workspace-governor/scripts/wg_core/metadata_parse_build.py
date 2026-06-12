from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_fields import metadata_field, metadata_value, project_type_from_text
from .metadata_registry import read_metadata_texts, review_analysis_registry


def parse_metadata_text(repo_root: Path) -> dict[str, Any]:
    agents_path = repo_root / "AGENTS.md"
    registry_path = repo_root / "analysis_registry.yaml"
    registry_text, agents_text = read_metadata_texts(repo_root)
    combined = f"{registry_text}\n{agents_text}"
    registry_review = review_analysis_registry(repo_root)
    signals: list[str] = []

    project_type, type_source = project_type_from_text(registry_text, agents_text)
    if project_type is not None:
        signals.append(f"{type_source}.project_type")

    domain, domain_source = metadata_field(registry_text, agents_text, "domain", slug_values=True)
    if domain is not None:
        signals.append(f"{domain_source}.domain")

    cloud_home_value, cloud_home_source = metadata_value(repo_root, "cloud_home")
    if cloud_home_value:
        signals.append(f"{cloud_home_source}.cloud_home")

    if project_type is None and "SideProjects/" in combined:
        project_type = "sideproject"
        signals.append("metadata.sideprojects-path")
    if project_type is None and "Research/" in combined:
        project_type = "research"
        signals.append("metadata.research-path")

    return {
        "agents_path": str(agents_path) if agents_path.exists() else None,
        "registry_path": str(registry_path) if registry_path.exists() else None,
        "project_type": project_type,
        "research_domain": domain,
        "cloud_home": cloud_home_value,
        "registry_review": registry_review,
        "signals": signals,
    }
