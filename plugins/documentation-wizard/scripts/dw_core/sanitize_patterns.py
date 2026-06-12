from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InfraPattern:
    regex: re.Pattern[str]
    fallback: str


PRIVATE_INFRA_PATTERNS = [
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:Library/CloudStorage/OneDrive(?:-Personal| - Personal)?)/[^\s`]+"),
        "the configured synced project home",
    ),
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:ProjectsRuntime)(?:/[^\s`]+)?"),
        "the configured runtime output directory",
    ),
    InfraPattern(
        re.compile(r"(?:~|/Users/[^/\s`]+)/(?:Projects)(?:/[^\s`]+)?"),
        "the local source checkout",
    ),
    InfraPattern(
        re.compile(r"/Users/[^\s`]+"),
        "the configured local path",
    ),
    InfraPattern(
        re.compile(r"OneDrive(?:-Personal| - Personal)?"),
        "the synced project home",
    ),
]

DATE_SEGMENT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILE_LIKE_SUFFIXES = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".adoc",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".pdf",
    ".py",
    ".R",
    ".r",
    ".qmd",
    ".ipynb",
    ".ts",
    ".js",
}
GENERATED_OUTPUT_ROOT_SEGMENTS = {
    "artifacts",
    "dashboard",
    "diagnostics",
    "figures",
    "logs",
    "output",
    "outputs",
    "plots",
    "results",
    "run",
    "runs",
}
