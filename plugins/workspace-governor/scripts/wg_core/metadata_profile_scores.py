from __future__ import annotations

import re
from pathlib import Path

from .metadata_parse_scalar import load_text

MEDICAL_NAME_RE = re.compile(r"(diabetes|t1dm|endocrin|oncolog|uveal|melanoma|clinical|patient|medical)", re.I)
SIDEPROJECT_NAME_RE = re.compile(r"(bracket|sports|hobby|game|fantasy|bet|mmbayes|ffbayes)", re.I)


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


def profile_corpus(repo_root: Path) -> str:
    return "\n".join(
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


def content_hits(corpus: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in corpus)


def profile_scores(
    repo_name: str,
    corpus: str,
    metadata: dict,
    software_signals: list[str],
) -> tuple[int, int, bool, bool, int, int]:
    research_terms = ["clinical", "patient", "diabetes", "t1dm", "oncolog", "uveal", "melanoma", "research"]
    sideproject_terms = ["bracket", "sports", "fantasy", "game", "side project"]
    research_content_hits = content_hits(corpus, research_terms)
    sideproject_content_hits = content_hits(corpus, sideproject_terms)
    research_name_hit = bool(MEDICAL_NAME_RE.search(repo_name))
    sideproject_name_hit = bool(SIDEPROJECT_NAME_RE.search(repo_name))

    research_score = (
        (4 if research_name_hit else 0)
        + (2 * research_content_hits)
        + (8 if metadata["project_type"] == "research" else 0)
    )
    sideproject_score = (
        (3 if sideproject_name_hit else 0)
        + (2 * sideproject_content_hits)
        + (8 if metadata["project_type"] == "sideproject" else 0)
    )
    return (
        research_score,
        sideproject_score,
        research_name_hit,
        sideproject_name_hit,
        research_content_hits,
        sideproject_content_hits,
    )
