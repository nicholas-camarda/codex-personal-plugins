from __future__ import annotations

from .metadata_parse import slugify


def parse_classifications(values: list[str]) -> dict[str, dict[str, str]]:
    mappings: dict[str, dict[str, str]] = {}
    for raw in values:
        name, spec = raw.split("=", 1)
        slug = slugify(name)
        if ":" in spec:
            kind, domain = spec.split(":", 1)
        else:
            kind, domain = spec, ""
        normalized = kind.strip().lower()
        if normalized not in {"research", "sideproject"}:
            raise ValueError(f"Invalid classification kind '{normalized}'")
        mappings[slug] = {"kind": normalized, "domain": slugify(domain) if domain else ""}
    return mappings


def parse_repo_kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    normalized = kind.strip().lower()
    if normalized not in {"research", "sideproject", "general"}:
        raise ValueError("Repo kind must be research, sideproject, or general.")
    return normalized
