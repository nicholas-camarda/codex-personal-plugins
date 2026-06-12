from __future__ import annotations

import re

SAFE_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
TEXT_SUFFIXES = {
    ".py", ".R", ".r", ".qmd", ".ipynb", ".md", ".txt", ".yaml", ".yml",
    ".json", ".toml", ".ini", ".cfg", ".sh",
}
IGNORED_PUBLIC_DOC_PARTS = {
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
