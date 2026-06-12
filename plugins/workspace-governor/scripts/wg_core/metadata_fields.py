from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_parse_scalar import extract_scalar, load_text, slugify


def metadata_value(repo_root: Path, key: str) -> tuple[str | None, str | None]:
    registry_text = load_text(repo_root / "analysis_registry.yaml")
    agents_text = load_text(repo_root / "AGENTS.md")
    registry_value = extract_scalar(registry_text, key)
    if registry_value is not None:
        return registry_value, "analysis_registry"
    agents_value = extract_scalar(agents_text, key)
    if agents_value is not None:
        return agents_value, "AGENTS.md"
    return None, None


def metadata_field(
    registry_text: str,
    agents_text: str,
    key: str,
    *,
    slug_values: bool = False,
) -> tuple[Any, str | None]:
    registry_value = extract_scalar(registry_text, key)
    if registry_value is not None:
        value = slugify(registry_value) if slug_values else registry_value
        return value, "analysis_registry"
    agents_value = extract_scalar(agents_text, key)
    if agents_value is not None:
        value = slugify(agents_value) if slug_values else agents_value
        return value, "AGENTS.md"
    return None, None


def project_type_from_text(registry_text: str, agents_text: str) -> tuple[str | None, str | None]:
    project_type, source = metadata_field(registry_text, agents_text, "project_type")
    if project_type is None:
        return None, None
    normalized = project_type.lower()
    if normalized not in {"research", "sideproject", "general"}:
        return None, None
    return normalized, source
