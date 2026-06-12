from __future__ import annotations

DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
PRIVATE_DOC_SEGMENTS = {"internal", "private"}
HIDDEN_DOC_SEGMENTS = {".git", ".history", ".codex"}
NON_PUBLIC_SEGMENTS = {
    "archive",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "migration_backups",
}
IGNORED_DIRS = HIDDEN_DOC_SEGMENTS | NON_PUBLIC_SEGMENTS
