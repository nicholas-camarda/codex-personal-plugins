from __future__ import annotations


import os
import re
from pathlib import Path
from typing import Any

from .roots import (
    GENERAL_REPO_CLOUD_ROOT,
    LEGACY_ROOT,
    PROJECTS_ROOT,
    RESEARCH_ROOT,
    RUNTIME_ROOT,
    SIDEPROJECTS_ROOT,
)

SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_layout",
    "publish_denylist",
}
MEDICAL_NAME_RE = re.compile(r"(diabetes|t1dm|endocrin|oncolog|uveal|melanoma|clinical|patient|medical)", re.I)
SIDEPROJECT_NAME_RE = re.compile(r"(bracket|sports|hobby|game|fantasy|bet|mmbayes|ffbayes)", re.I)
IGNORED_AUDIT_CHILD_DIRS = {
    "archive",
    ".agent-os",
    ".codex",
    "node_modules",
    ".git",
    ".history",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "migration_backups",
}


def load_text(path: Path, limit: int = 64000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def read_metadata_texts(repo_root: Path) -> tuple[str, str]:
    return load_text(repo_root / "analysis_registry.yaml"), load_text(repo_root / "AGENTS.md")


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def review_analysis_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
            "message": None,
        }

    keys = top_level_yaml_keys(load_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    message = None
    if unsupported:
        supported_list = ", ".join(sorted(SUPPORTED_ANALYSIS_REGISTRY_KEYS))
        message = (
            "analysis_registry.yaml contains unsupported top-level keys "
            f"({', '.join(unsupported)}). Supported keys are: {supported_list}."
        )
    return {
        "path": str(path),
        "exists": True,
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
        "message": message,
    }


def extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("'\"`")


def extract_list(text: str, key: str) -> list[str]:
    inline = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$", text)
    if inline:
        values = []
        for item in inline.group(1).split(","):
            normalized = item.strip().strip("'\"`")
            if normalized:
                values.append(normalized)
        return values

    lines = text.splitlines()
    values: list[str] = []
    active = False
    base_indent = 0
    key_pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*$")
    for line in lines:
        if not active:
            match = key_pattern.match(line)
            if not match:
                continue
            active = True
            base_indent = len(match.group(1))
            continue
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip(" "))
        if not stripped:
            continue
        if current_indent <= base_indent and not stripped.startswith("- "):
            break
        bullet_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if bullet_match:
            values.append(bullet_match.group(1).strip().strip("'\"`"))
            continue
        break
    return values


def metadata_value(repo_root: Path, key: str) -> tuple[str | None, str | None]:
    registry_text, agents_text = read_metadata_texts(repo_root)
    registry_value = extract_scalar(registry_text, key)
    if registry_value is not None:
        return registry_value, "analysis_registry"
    agents_value = extract_scalar(agents_text, key)
    if agents_value is not None:
        return agents_value, "AGENTS.md"
    return None, None


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unnamed"


def repo_software_signals(repo_root: Path) -> list[str]:
    signals: list[str] = []
    file_names = [
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "Makefile",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "tsconfig.json",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "justfile",
    ]
    dir_names = ["src", "tests", "test", "app", "apps", "lib", "pkg", "bin"]

    for name in file_names:
        if (repo_root / name).is_file():
            signals.append(name)
    for name in dir_names:
        if (repo_root / name).is_dir():
            signals.append(f"{name}/")
    return signals


def parse_metadata_text(repo_root: Path) -> dict[str, Any]:
    agents_path = repo_root / "AGENTS.md"
    registry_path = repo_root / "analysis_registry.yaml"
    registry_text, agents_text = read_metadata_texts(repo_root)
    combined = f"{registry_text}\n{agents_text}"
    registry_review = review_analysis_registry(repo_root)
    project_type = None
    domain = None
    cloud_home = None
    signals: list[str] = []

    registry_type = extract_scalar(registry_text, "project_type")
    if registry_type and registry_type.lower() in {"research", "sideproject", "general"}:
        project_type = registry_type.lower()
        signals.append("analysis_registry.project_type")
    else:
        agents_type = extract_scalar(agents_text, "project_type")
        if agents_type and agents_type.lower() in {"research", "sideproject", "general"}:
            project_type = agents_type.lower()
            signals.append("AGENTS.md.project_type")

    registry_domain = extract_scalar(registry_text, "domain")
    if registry_domain:
        domain = slugify(registry_domain)
        signals.append("analysis_registry.domain")
    else:
        agents_domain = extract_scalar(agents_text, "domain")
        if agents_domain:
            domain = slugify(agents_domain)
            signals.append("AGENTS.md.domain")

    cloud_home_value, cloud_home_source = metadata_value(repo_root, "cloud_home")
    if cloud_home_value:
        cloud_home = cloud_home_value
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
        "cloud_home": cloud_home,
        "registry_review": registry_review,
        "signals": signals,
    }


def infer_project_profile(repo_root: Path, repo_name: str) -> dict[str, Any]:
    metadata = parse_metadata_text(repo_root)
    software_signals = repo_software_signals(repo_root)
    files = {
        "readmes": sorted(str(p) for p in repo_root.glob("README*")),
        "agents": metadata["agents_path"],
        "registry": metadata["registry_path"],
        "notebooks": sorted(str(p) for p in repo_root.glob("*.ipynb")),
        "r_files": sorted(str(p) for p in repo_root.glob("*.R")),
        "configs": sorted(str(p) for p in repo_root.glob("config.*")),
        "rproj": sorted(str(p) for p in repo_root.glob("*.Rproj")),
    }

    corpus = "\n".join(
        load_text(candidate)
        for candidate in [
            repo_root / "README.md",
            repo_root / "README.txt",
            repo_root / "config.yml",
            repo_root / "config.yaml",
            repo_root / "config.json",
            repo_root / "AGENTS.md",
            repo_root / "analysis_registry.yaml",
        ]
        if candidate.exists()
    ).lower()

    research_terms = ["clinical", "patient", "diabetes", "t1dm", "oncolog", "uveal", "melanoma", "research"]
    sideproject_terms = ["bracket", "sports", "fantasy", "game", "side project"]
    research_content_hits = sum(1 for term in research_terms if term in corpus)
    sideproject_content_hits = sum(1 for term in sideproject_terms if term in corpus)
    research_name_hit = bool(MEDICAL_NAME_RE.search(repo_name))
    sideproject_name_hit = bool(SIDEPROJECT_NAME_RE.search(repo_name))

    research_score = (4 if research_name_hit else 0) + (2 * research_content_hits) + (8 if metadata["project_type"] == "research" else 0)
    sideproject_score = (3 if sideproject_name_hit else 0) + (2 * sideproject_content_hits) + (8 if metadata["project_type"] == "sideproject" else 0)

    existing_cloud_side = SIDEPROJECTS_ROOT / repo_name
    existing_cloud_research = RESEARCH_ROOT / repo_name if (RESEARCH_ROOT / repo_name).exists() else None

    if metadata["project_type"]:
        profile = metadata["project_type"]
        profile_reason = "repo metadata"
    elif existing_cloud_side.exists() and existing_cloud_research is None:
        profile = "sideproject"
        profile_reason = "existing sideprojects footprint"
    elif existing_cloud_research is not None and not existing_cloud_side.exists():
        profile = "research"
        profile_reason = "existing research footprint"
    elif (
        research_score > sideproject_score
        and research_score >= 4
        and (metadata["research_domain"] or research_content_hits >= 2 or (research_name_hit and not software_signals))
    ):
        profile = "research"
        profile_reason = "research domain signals"
    elif (
        sideproject_score > research_score
        and sideproject_score >= 4
        and (sideproject_content_hits >= 2 or (sideproject_name_hit and not software_signals))
    ):
        profile = "sideproject"
        profile_reason = "sideproject signals"
    else:
        profile = "general"
        profile_reason = "standard software-repo signals" if software_signals else "weak domain evidence"

    confidence = 0.18 + min(0.62, abs(research_score - sideproject_score) / 12)
    if profile == "general":
        confidence = 0.35 if software_signals else 0.25
    if metadata["project_type"]:
        confidence = max(confidence, 0.9)
    if metadata["research_domain"]:
        confidence = max(confidence, 0.92)

    return {
        "repo_name": repo_name,
        "files": files,
        "software_signals": software_signals,
        "scores": {"research": research_score, "sideproject": sideproject_score},
        "profile_guess": profile,
        "confidence": round(min(confidence, 0.99), 2),
        "research_domain": metadata["research_domain"],
        "metadata": metadata,
        "existing_footprints": {
            "projects": (PROJECTS_ROOT / repo_name).exists(),
            "runtime": (RUNTIME_ROOT / repo_name).exists(),
            "sideprojects": existing_cloud_side.exists(),
            "research": existing_cloud_research is not None,
            "research_path": str(existing_cloud_research) if existing_cloud_research else None,
        },
        "profile_reason": profile_reason,
        "general_mode": profile == "general",
        "has_legacy_paths": any(
            marker in corpus
            for marker in [
                "desktop/coding",
                "~/desktop/coding",
                str(LEGACY_ROOT).lower(),
                "onedrive-personal/desktop/coding",
                "onedrive - personal/desktop/coding",
            ]
        ),
    }


