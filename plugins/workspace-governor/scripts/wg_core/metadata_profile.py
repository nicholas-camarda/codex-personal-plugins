from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_parse import parse_metadata_text
from .metadata_profile_scores import profile_corpus, profile_scores, repo_software_signals
from .metadata_profile_select import profile_confidence, select_profile
from .metadata_registry import read_metadata_texts, review_analysis_registry
from .roots import LEGACY_ROOT, PROJECTS_ROOT, RESEARCH_ROOT, RUNTIME_ROOT, SIDEPROJECTS_ROOT


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

    corpus = profile_corpus(repo_root)
    (
        research_score,
        sideproject_score,
        research_name_hit,
        sideproject_name_hit,
        research_content_hits,
        sideproject_content_hits,
    ) = profile_scores(repo_name, corpus, metadata, software_signals)
    profile, profile_reason = select_profile(
        metadata,
        repo_name,
        research_score,
        sideproject_score,
        research_name_hit,
        sideproject_name_hit,
        research_content_hits,
        sideproject_content_hits,
        software_signals,
    )
    confidence = profile_confidence(profile, metadata, research_score, sideproject_score, software_signals)

    existing_cloud_side = SIDEPROJECTS_ROOT / repo_name
    existing_cloud_research = RESEARCH_ROOT / repo_name if (RESEARCH_ROOT / repo_name).exists() else None
    legacy_markers = [
        "desktop/coding",
        "~/desktop/coding",
        str(LEGACY_ROOT).lower(),
        "onedrive-personal/desktop/coding",
        "onedrive - personal/desktop/coding",
    ]

    return {
        "repo_name": repo_name,
        "files": files,
        "software_signals": software_signals,
        "scores": {"research": research_score, "sideproject": sideproject_score},
        "profile_guess": profile,
        "confidence": confidence,
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
        "has_legacy_paths": any(marker in corpus for marker in legacy_markers),
    }
