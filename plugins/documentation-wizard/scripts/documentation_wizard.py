#!/usr/bin/env python3
"""Helper CLI for documentation-wizard."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
TEXT_SUFFIXES = DOC_SUFFIXES | {".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".ts", ".js"}
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?:~?/|/|\./|\../)?[A-Za-z0-9_./<>{}-]+(?:\.[A-Za-z0-9_./<>{}-]+)+"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
FLAG_RE = re.compile(r"--[A-Za-z0-9][A-Za-z0-9_-]*")
BACKTICK_RE = re.compile(r"`([^`]+)`")
ARGPARSE_CALL_RE = re.compile(r"add_argument\((.*?)\)", re.S)
CLICK_OPTION_CALL_RE = re.compile(r"(?:click\.option|typer\.Option)\((.*?)\)", re.S)
TYPER_OPTION_IMPORT_RE = re.compile(r"\bfrom\s+typer\s+import\b|\bimport\s+typer\b")
COMMAND_MODULE_RE = re.compile(r"module=['\"]([^'\"]+)['\"]")

PLUGIN_NAME = "documentation-wizard"
PLUGIN_DISPLAY_NAME = "Documentation Wizard"
EXPECTED_SKILLS_PATH = "./skills/"
HOME_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
HOME_PLUGIN_ROOT = Path.home() / ".codex" / "plugins" / PLUGIN_NAME
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
DOMAIN_LIKE_RE = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/?$")
VERSION_LIKE_RE = re.compile(r"^\d+(?:\.\d+)+$")
ABBREVIATION_LIKE_RE = re.compile(r"^(?:[A-Z]\.)+[A-Z]?$")
DATE_SEGMENT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PATH_CONTINUATION_CHARS = set("_-<>{}()[]")
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
SUPPORTED_ANALYSIS_REGISTRY_KEYS = {
    "project_slug",
    "project_type",
    "domain",
    "cloud_home",
    "runtime_home",
    "publish_root_name",
    "publish_denylist",
}


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


def _portable_tail(path_text: str, min_parts: int = 2) -> str | None:
    trailing_slash = path_text.endswith("/")
    trimmed = path_text.rstrip("/")
    if not trimmed:
        return None
    parts = [part for part in trimmed.split("/") if part and part != "~"]
    if not parts:
        return None
    count = min(len(parts), max(1, min_parts))
    tail = "/".join(parts[-count:])
    if trailing_slash:
        return f"{tail}/"
    return tail


def portable_public_replacement(path_text: str, fallback: str) -> str:
    trailing_slash = path_text.endswith("/")
    parts = [part for part in path_text.rstrip("/").split("/") if part and part != "~"]

    def join_tail(tail_parts: list[str]) -> str:
        tail = "/".join(tail_parts)
        if trailing_slash:
            return f"{tail}/"
        return tail

    def portable_suffix_after(marker: str, marker_fallback: str) -> str | None:
        if marker not in parts:
            return None
        marker_index = parts.index(marker)
        suffix_parts = parts[marker_index + 2 :]
        if not suffix_parts:
            return marker_fallback
        if len(suffix_parts) == 1:
            segment = suffix_parts[0]
            if (
                segment.lower() in GENERATED_OUTPUT_ROOT_SEGMENTS
                or DATE_SEGMENT_RE.fullmatch(segment)
                or Path(segment).suffix.lower() in {item.lower() for item in FILE_LIKE_SUFFIXES}
            ):
                return join_tail(suffix_parts)
            return marker_fallback
        return join_tail(suffix_parts[-2:])

    for marker, marker_fallback in [
        ("ProjectsRuntime", "the configured runtime output directory"),
        ("Projects", "the local source checkout"),
        ("SideProjects", "the configured synced project home"),
        ("Research", "the configured synced project home"),
    ]:
        replacement = portable_suffix_after(marker, marker_fallback)
        if replacement is not None:
            return replacement

    generic_tail = _portable_tail(path_text, min_parts=2)
    return generic_tail or fallback


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def marketplace_root(path: Path) -> Path:
    return path.parents[2]


def marketplace_entry_by_name(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any] | None:
    for item in marketplace.get("plugins", []):
        if isinstance(item, dict) and item.get("name") == plugin_name:
            return item
    return None


def marketplace_entry_has_required_metadata(entry: dict[str, Any] | None) -> bool:
    if not isinstance(entry, dict):
        return False
    source = entry.get("source")
    policy = entry.get("policy")
    return (
        isinstance(source, dict)
        and source.get("source") == "local"
        and isinstance(source.get("path"), str)
        and str(source.get("path")).startswith("./")
        and isinstance(policy, dict)
        and isinstance(policy.get("installation"), str)
        and isinstance(policy.get("authentication"), str)
        and isinstance(entry.get("category"), str)
    )


def marketplace_entry_resolves_to(
    entry: dict[str, Any] | None,
    marketplace_path: Path | None,
    target_path: Path,
) -> bool:
    if not isinstance(entry, dict) or marketplace_path is None:
        return False
    source = entry.get("source")
    if not isinstance(source, dict):
        return False
    relative_path = source.get("path")
    if not isinstance(relative_path, str) or not relative_path.startswith("./"):
        return False
    resolved_target = (marketplace_root(marketplace_path) / relative_path[2:]).resolve()
    return resolved_target == target_path.resolve()


def iter_files(root: Path, suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".")
            and name.lower() not in HIDDEN_DOC_SEGMENTS
            and name.lower() not in NON_PUBLIC_SEGMENTS
        ]
        current = Path(dirpath)
        rel_dir = current.relative_to(root)
        if rel_dir != Path(".") and any(part.startswith(".") or part.lower() in NON_PUBLIC_SEGMENTS for part in rel_dir.parts):
            continue
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() not in suffixes:
                continue
            files.append(path)
    return sorted(files)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_public_doc(rel_path: str) -> bool:
    rel = Path(rel_path)
    name = rel.name.lower()
    if ".local." in name:
        return False
    if any(part.startswith(".") for part in rel.parts[:-1]):
        return False
    if any(part.lower() in HIDDEN_DOC_SEGMENTS for part in rel.parts):
        return False
    if any(part.lower() in NON_PUBLIC_SEGMENTS for part in rel.parts):
        return False
    if any(part.lower() in PRIVATE_DOC_SEGMENTS for part in rel.parts):
        return False
    return True


def looks_like_non_path_token(token: str) -> bool:
    normalized = token.strip()
    if not normalized:
        return True
    if normalized.startswith("//"):
        return True
    if VERSION_LIKE_RE.fullmatch(normalized):
        return True
    if DOMAIN_LIKE_RE.fullmatch(normalized):
        return True
    return False


def looks_like_dotted_identifier(token: str) -> bool:
    normalized = token.rstrip(".,:;)")
    if "/" in normalized or normalized.startswith(("~", "/", "./", "../")):
        return False
    if ABBREVIATION_LIKE_RE.fullmatch(normalized):
        return True
    if "." not in normalized:
        return False
    suffix = Path(normalized).suffix
    return suffix.lower() not in {item.lower() for item in FILE_LIKE_SUFFIXES}


def looks_like_template_path(token: str) -> bool:
    return any(marker in token for marker in ("<", ">", "{", "}"))


def is_file_like_token(token: str) -> bool:
    normalized = token.rstrip(".,:;)")
    if "/" in normalized:
        if normalized.startswith("/") and normalized.count("/") == 1:
            suffix = Path(normalized).suffix
            return suffix.lower() in {item.lower() for item in FILE_LIKE_SUFFIXES}
        return True
    suffix = Path(normalized).suffix
    return suffix.lower() in {item.lower() for item in FILE_LIKE_SUFFIXES}


def normalize_path_token(token: str) -> str:
    normalized = token.strip().rstrip(".,:;)")
    normalized = normalized.split("#", 1)[0]
    normalized = normalized.split("?", 1)[0]
    return normalized


def referenced_path_exists(root: Path, doc_rel_path: str, token: str) -> bool:
    normalized = normalize_path_token(token)
    if normalized.startswith("~"):
        return Path(normalized).expanduser().exists()
    if normalized.startswith("/"):
        return Path(normalized).exists()
    doc_parent = (root / doc_rel_path).parent
    candidates = [(doc_parent / normalized).resolve()]
    if not normalized.startswith(("./", "../")):
        candidates.append((root / normalized).resolve())
    return any(candidate.exists() for candidate in candidates)


def is_valid_relative_doc_link(root: Path, doc_rel_path: str, token: str) -> bool:
    normalized = normalize_path_token(token)
    suffix = Path(normalized).suffix.lower()
    if suffix not in {item.lower() for item in DOC_SUFFIXES}:
        return False
    doc_parent = (root / doc_rel_path).parent
    candidates = [(doc_parent / normalized).resolve()]
    if not normalized.startswith(("./", "../")):
        candidates.append((root / normalized).resolve())
    return any(candidate.exists() for candidate in candidates)


def looks_like_generated_output_path(token: str) -> bool:
    normalized = normalize_path_token(token)
    if normalized.startswith(("~", "/", "./", "../")):
        return False
    parts = Path(normalized).parts
    return bool(parts) and parts[0].lower() in GENERATED_OUTPUT_ROOT_SEGMENTS


def locate_line(path: Path, token: str) -> int | None:
    for index, line in enumerate(read_text(path).splitlines(), start=1):
        if token in line:
            return index
    return None


def top_level_yaml_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*", line)
        if match:
            keys.append(match.group(1))
    return keys


def analysis_registry_review(root: Path) -> dict[str, Any]:
    path = root / "analysis_registry.yaml"
    if not path.exists():
        return {
            "exists": False,
            "path": "analysis_registry.yaml",
            "supported": True,
            "top_level_keys": [],
            "unsupported_top_level_keys": [],
        }
    keys = top_level_yaml_keys(read_text(path))
    unsupported = [key for key in keys if key not in SUPPORTED_ANALYSIS_REGISTRY_KEYS]
    return {
        "exists": True,
        "path": "analysis_registry.yaml",
        "supported": not unsupported,
        "top_level_keys": keys,
        "unsupported_top_level_keys": unsupported,
    }


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



def public_cli_surface_paths(root: Path) -> list[Path]:
    cli_modules: set[Path] = set()
    for cli_path in root.glob('src/**/cli.py'):
        text = read_text(cli_path)
        if 'CommandSpec(' not in text:
            continue
        cli_modules.add(cli_path.resolve())
        for module_name in COMMAND_MODULE_RE.findall(text):
            module_path = root / 'src' / Path(*module_name.split('.')).with_suffix('.py')
            if module_path.exists():
                cli_modules.add(module_path.resolve())
    return sorted(cli_modules)


def extract_cli_flags(path: Path, root: Path) -> list[dict[str, Any]]:
    text = read_text(path)
    results: list[dict[str, Any]] = []
    for call in ARGPARSE_CALL_RE.findall(text):
        for flag in FLAG_RE.findall(call):
            results.append(
                {
                    "flag": flag,
                    "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                }
            )
    for call in CLICK_OPTION_CALL_RE.findall(text):
        for flag in FLAG_RE.findall(call):
            results.append(
                {
                    "flag": flag,
                    "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                }
            )
    if TYPER_OPTION_IMPORT_RE.search(text):
        for call in re.findall(r"(?<!\.)Option\((.*?)\)", text, re.S):
            for flag in FLAG_RE.findall(call):
                results.append(
                    {
                        "flag": flag,
                        "source_ref": f"{relative(path, root)}:{locate_line(path, flag) or 1}",
                    }
                )
    return results


def walk_schema(prefix: str, payload: dict[str, Any], sink: list[dict[str, Any]], source_ref: str) -> None:
    for key, spec in (payload.get("properties") or {}).items():
        dotted = f"{prefix}.{key}" if prefix else key
        sink.append(
            {
                "key": dotted,
                "default": spec.get("default"),
                "source_ref": source_ref,
            }
        )
        if isinstance(spec, dict):
            walk_schema(dotted, spec, sink, source_ref)


def extract_interfaces(root: Path) -> dict[str, Any]:
    cli_flags: list[dict[str, Any]] = []
    config_keys: list[dict[str, Any]] = []
    referenced_paths: list[dict[str, Any]] = []

    public_cli_paths = public_cli_surface_paths(root)
    cli_sources = public_cli_paths or list(iter_files(root, {".py"}))
    for path in cli_sources:
        cli_flags.extend(extract_cli_flags(path, root))

    for path in iter_files(root, {".json"}):
        if not path.name.endswith(".schema.json"):
            continue
        source_ref = relative(path, root)
        try:
            payload = json.loads(read_text(path))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            walk_schema("", payload, config_keys, source_ref)

    for path in inventory_docs(root)["public_doc_surfaces"]:
        doc_path = root / path
        text = read_text(doc_path)
        candidates: list[tuple[str, int, int, bool]] = []
        candidates.extend((match.group(1), match.start(1), match.end(1), True) for match in MARKDOWN_LINK_RE.finditer(text))
        candidates.extend((match.group(0), match.start(0), match.end(0), False) for match in PATH_TOKEN_RE.finditer(text))
        seen_tokens: set[str] = set()
        for token, start, end, explicit_link in candidates:
            normalized = normalize_path_token(token)
            if not normalized or normalized in seen_tokens:
                continue
            seen_tokens.add(normalized)
            if token.startswith("http"):
                continue
            if normalized.startswith(("http://", "https://", "mailto:")):
                continue
            if looks_like_non_path_token(normalized):
                continue
            if looks_like_dotted_identifier(normalized):
                continue
            if not is_file_like_token(normalized):
                continue
            next_char = text[end] if end < len(text) else ""
            prev_char = text[start - 1] if start > 0 else ""
            if prev_char in {"<", ">"} or next_char in {"<", ">"}:
                continue
            if not explicit_link and next_char and (next_char.isalnum() or next_char in PATH_CONTINUATION_CHARS):
                continue
            if not explicit_link and prev_char and (prev_char.isalnum() or prev_char in {"_", "-"}):
                continue
            if looks_like_template_path(normalized):
                continue
            if is_valid_relative_doc_link(root, path, normalized):
                continue
            if looks_like_generated_output_path(normalized):
                continue
            referenced_paths.append(
                {
                    "path": normalized,
                    "doc_ref": f"{path}:{locate_line(doc_path, token) or 1}",
                    "exists": referenced_path_exists(root, path, normalized),
                }
            )

    return {
        "repo_root": str(root),
        "cli_flags": sorted({item["flag"]: item for item in cli_flags}.values(), key=lambda item: item["flag"]),
        "config_keys": sorted({item["key"]: item for item in config_keys}.values(), key=lambda item: item["key"]),
        "referenced_paths": referenced_paths,
    }


def documented_tokens(root: Path) -> dict[str, dict[str, str]]:
    flags: dict[str, str] = {}
    config_keys: dict[str, str] = {}
    for rel_path in inventory_docs(root)["public_doc_surfaces"]:
        path = root / rel_path
        text = read_text(path)
        for flag in FLAG_RE.findall(text):
            flags.setdefault(flag, f"{rel_path}:{locate_line(path, flag) or 1}")
        for token in BACKTICK_RE.findall(text):
            if "/" in token or token.startswith("--"):
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", token):
                config_keys.setdefault(token, f"{rel_path}:{locate_line(path, token) or 1}")
    return {"flags": flags, "config_keys": config_keys}


def closest_match(token: str, candidates: list[str]) -> str | None:
    matches = difflib.get_close_matches(token, candidates, n=1, cutoff=0.5)
    return matches[0] if matches else None


def find_private_infra_leaks(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rel_path in inventory_docs(root)["public_doc_surfaces"]:
        path = root / rel_path
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            line_matches: list[tuple[int, int, str, str]] = []
            for pattern in PRIVATE_INFRA_PATTERNS:
                for match in pattern.regex.finditer(line):
                    replacement = portable_public_replacement(match.group(0), pattern.fallback)
                    line_matches.append((match.start(), match.end(), match.group(0), replacement))
            line_matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
            accepted: list[tuple[int, int, str, str]] = []
            for candidate in line_matches:
                start, end, _, _ = candidate
                if any(start >= kept_start and end <= kept_end for kept_start, kept_end, _, _ in accepted):
                    continue
                accepted.append(candidate)
            for _, _, matched_text, replacement in accepted:
                findings.append(
                    {
                        "kind": "private-infra-leak",
                        "severity": "P1",
                        "evidence_basis": "Direct",
                        "doc_ref": f"{rel_path}:{line_number}",
                        "source_ref": "public-doc-policy",
                        "message": f"Public doc exposes maintainer-specific infrastructure detail `{matched_text}`.",
                        "impact": "Collaborators see maintainer-only storage topology instead of portable setup guidance.",
                        "patch_direction": f"Replace `{matched_text}` with `{replacement}` in {rel_path} and keep the concrete path in AGENTS.md or internal docs.",
                        "replacement": replacement,
                    }
                )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (finding["doc_ref"], finding["message"])
        unique.setdefault(key, finding)
    return list(unique.values())


def sanitize_public_docs(root: Path, write: bool = False) -> dict[str, Any]:
    rewrites: list[dict[str, Any]] = []
    changed_files = 0
    for rel_path in inventory_docs(root)["public_doc_surfaces"]:
        path = root / rel_path
        original_text = read_text(path)
        updated_text = original_text
        replacements: list[dict[str, Any]] = []
        for pattern in PRIVATE_INFRA_PATTERNS:
            def replacement_for_match(match: re.Match[str]) -> str:
                replacement = portable_public_replacement(match.group(0), pattern.fallback)
                replacements.append(
                    {
                        "matched": match.group(0),
                        "replacement": replacement,
                    }
                )
                return replacement

            updated_text = pattern.regex.sub(replacement_for_match, updated_text)
        if updated_text == original_text:
            continue
        changed_files += 1
        rewrites.append(
            {
                "path": rel_path,
                "changed": True,
                "write": bool(write),
                "replacements": replacements,
            }
        )
        if write:
            path.write_text(updated_text, encoding="utf-8")
    return {
        "repo_root": str(root),
        "write": bool(write),
        "changed_files": changed_files,
        "rewrites": rewrites,
    }


def build_report(root: Path) -> dict[str, Any]:
    inventory = inventory_docs(root)
    interfaces = extract_interfaces(root)
    docs = documented_tokens(root)

    cli_flags = {item["flag"]: item for item in interfaces["cli_flags"]}
    config_keys = {item["key"]: item for item in interfaces["config_keys"]}
    findings: list[dict[str, Any]] = []
    registry_review = inventory.get("analysis_registry_review") or {}

    if registry_review.get("exists") and not registry_review.get("supported", True):
        unsupported = ", ".join(registry_review.get("unsupported_top_level_keys") or [])
        findings.append(
            {
                "kind": "unsupported-analysis-registry-shape",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": "analysis_registry.yaml",
                "source_ref": "analysis_registry.yaml",
                "message": f"analysis_registry.yaml uses unsupported top-level keys ({unsupported}).",
                "impact": "Tooling may silently ignore most of the file and leave misleading metadata in place.",
                "patch_direction": (
                    "Rewrite analysis_registry.yaml to the supported top-level metadata contract: "
                    "project_slug, project_type, domain, cloud_home, runtime_home, publish_root_name, publish_denylist."
                ),
            }
        )

    for flag, doc_ref in docs["flags"].items():
        if flag in cli_flags:
            continue
        suggestion = closest_match(flag, sorted(cli_flags))
        patch = f"Replace `{flag}` with `{suggestion}` in {doc_ref.split(':', 1)[0]}" if suggestion else f"Remove or correct `{flag}` in {doc_ref.split(':', 1)[0]}"
        findings.append(
            {
                "kind": "stale-cli-flag",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": cli_flags.get(suggestion, {}).get("source_ref") if suggestion else "missing-live-flag",
                "message": f"Documented flag `{flag}` does not appear in the live CLI surface.",
                "impact": "Users may copy a command that no longer parses.",
                "patch_direction": patch,
            }
        )

    for flag, source in cli_flags.items():
        if flag in docs["flags"]:
            continue
        findings.append(
            {
                "kind": "missing-cli-flag",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live flag `{flag}` is not documented.",
                "impact": "Users may miss supported behavior or defaults.",
                "patch_direction": f"Document `{flag}` in the canonical usage docs.",
            }
        )

    for key, doc_ref in docs["config_keys"].items():
        if key in config_keys:
            continue
        suggestion = closest_match(key, sorted(config_keys))
        if not suggestion:
            continue
        findings.append(
            {
                "kind": "stale-config-key",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": doc_ref,
                "source_ref": config_keys[suggestion]["source_ref"],
                "message": f"Documented config key `{key}` does not exist in the live schema.",
                "impact": "Users may set the wrong config key and get ignored behavior.",
                "patch_direction": f"Replace `{key}` with `{suggestion}` in {doc_ref.split(':', 1)[0]}",
            }
        )

    for key, source in config_keys.items():
        if key in docs["config_keys"]:
            continue
        findings.append(
            {
                "kind": "missing-config-key",
                "severity": "P2",
                "evidence_basis": "Direct",
                "doc_ref": "missing-from-docs",
                "source_ref": source["source_ref"],
                "message": f"Live config key `{key}` is not documented.",
                "impact": "Users may not know a supported schema option exists.",
                "patch_direction": f"Document `{key}` in the configuration reference.",
            }
        )

    for ref in interfaces["referenced_paths"]:
        if ref["exists"]:
            continue
        findings.append(
            {
                "kind": "broken-referenced-path",
                "severity": "P1",
                "evidence_basis": "Direct",
                "doc_ref": ref["doc_ref"],
                "source_ref": "filesystem",
                "message": f"Referenced path `{ref['path']}` does not exist.",
                "impact": "Users may follow a broken path or setup step.",
                "patch_direction": f"Update or remove `{ref['path']}` in {ref['doc_ref'].split(':', 1)[0]}",
            }
        )

    findings.extend(find_private_infra_leaks(root))

    return {
        "repo_root": str(root),
        "scope": "documentation-drift-audit",
        "artifact_map": {
            "doc_surfaces": inventory["doc_surfaces"],
            "public_doc_surfaces": inventory["public_doc_surfaces"],
            "source_truth_candidates": inventory["source_truth_candidates"],
        },
        "findings": findings,
        "direct_evidence_vs_inference": "All findings in this report are grounded in repo files, argparse definitions, JSON schema files, and filesystem checks.",
        "required_tests_checks": [
            "Run the generated regression check for the highest-risk drift class.",
        ],
        "recommended_actions": [finding["patch_direction"] for finding in findings[:5]],
    }


def regression_check(root: Path, kind: str) -> dict[str, Any]:
    failure_kind = "stale-cli-flag" if kind == "cli-flags" else kind
    command = f'python3 "{Path(__file__).resolve()}" report --repo "{root}"'
    script = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# generated from documentation_wizard.py report",
            f"report_json=$({command})",
            f'echo "$report_json" | python3 -c \'import json,sys; data=json.load(sys.stdin); bad=[f for f in data.get("findings", []) if f.get("kind") == "{failure_kind}"]; raise SystemExit(1 if bad else 0)\'',
        ]
    )
    return {"repo_root": str(root), "kind": kind, "script": script}


def validate_plugin(root: Path) -> dict[str, Any]:
    plugin_root = root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    home_marketplace = load_json(HOME_MARKETPLACE_PATH) if HOME_MARKETPLACE_PATH.exists() else {}
    readme_text = read_text(plugin_root / "README.md")
    top_level_skill = read_text(plugin_root / "skills" / PLUGIN_NAME / "SKILL.md")

    home_registered_entry = marketplace_entry_by_name(home_marketplace, PLUGIN_NAME)
    icon_path = plugin_root / manifest["interface"]["composerIcon"].replace("./", "")
    logo_path = plugin_root / manifest["interface"]["logo"].replace("./", "")

    checks = [
        {"name": "manifest-name", "passed": manifest.get("name") == PLUGIN_NAME},
        {"name": "display-name", "passed": manifest.get("interface", {}).get("displayName") == PLUGIN_DISPLAY_NAME},
        {"name": "skills-path", "passed": manifest.get("skills") == EXPECTED_SKILLS_PATH},
        {"name": "marketplace-registration", "passed": home_registered_entry is not None},
        {
            "name": "marketplace-entry-path",
            "passed": marketplace_entry_resolves_to(home_registered_entry, HOME_MARKETPLACE_PATH, HOME_PLUGIN_ROOT),
        },
        {"name": "marketplace-entry-metadata", "passed": marketplace_entry_has_required_metadata(home_registered_entry)},
        {"name": "plugin-root-is-home-root", "passed": plugin_root.resolve() == HOME_PLUGIN_ROOT.resolve()},
        {"name": "home-plugin-root", "passed": HOME_PLUGIN_ROOT.exists()},
        {"name": "home-plugin-manifest", "passed": (HOME_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").exists()},
        {"name": "no-fake-urls", "passed": "example.com" not in json.dumps(manifest)},
        {"name": "top-level-skill", "passed": f"name: {PLUGIN_NAME}" in top_level_skill},
        {"name": "mention-docs", "passed": "@documentation-wizard" in readme_text},
        {"name": "icon-exists", "passed": icon_path.exists()},
        {"name": "logo-exists", "passed": logo_path.exists()},
    ]
    passed = all(check["passed"] for check in checks)
    return {"plugin": PLUGIN_NAME, "passed": passed, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="documentation-wizard helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="List documentation surfaces and source-of-truth candidates")
    inventory_parser.add_argument("--repo", required=True)

    interfaces_parser = subparsers.add_parser("interfaces", help="Extract live CLI flags, config keys, and referenced paths")
    interfaces_parser.add_argument("--repo", required=True)

    report_parser = subparsers.add_parser("report", help="Generate a documentation drift report")
    report_parser.add_argument("--repo", required=True)

    regression_parser = subparsers.add_parser("regression-check", help="Generate a lightweight regression check")
    regression_parser.add_argument("--repo", required=True)
    regression_parser.add_argument("--kind", required=True, choices=["cli-flags", "config-schema", "referenced-paths", "private-infra"])

    sanitize_parser = subparsers.add_parser("sanitize-public-docs", help="Rewrite public docs to remove maintainer-specific infrastructure details")
    sanitize_parser.add_argument("--repo", required=True)
    sanitize_parser.add_argument("--write", action="store_true", help="Apply the sanitized rewrites to disk")

    subparsers.add_parser("validate", help="Validate local plugin registration and assets")

    args = parser.parse_args()
    if args.command == "validate":
        payload = validate_plugin(Path(__file__).resolve().parent)
    else:
        root = Path(args.repo).expanduser().resolve()
        if args.command == "inventory":
            payload = inventory_docs(root)
        elif args.command == "interfaces":
            payload = extract_interfaces(root)
        elif args.command == "report":
            payload = build_report(root)
        elif args.command == "sanitize-public-docs":
            payload = sanitize_public_docs(root, write=bool(args.write))
        else:
            kind_map = {
                "cli-flags": "cli-flags",
                "config-schema": "stale-config-key",
                "referenced-paths": "broken-referenced-path",
                "private-infra": "private-infra-leak",
            }
            payload = regression_check(root, kind_map[args.kind])
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
