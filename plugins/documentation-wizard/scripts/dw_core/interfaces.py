from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .files import DOC_SUFFIXES, iter_files, public_doc_surfaces, read_text, relative


PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?:~?/|/|\./|\../)?[A-Za-z0-9_./<>{}-]+(?:\.[A-Za-z0-9_./<>{}-]+)+"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
FLAG_RE = re.compile(r"--[A-Za-z0-9][A-Za-z0-9_-]*")
ARGPARSE_CALL_RE = re.compile(r"add_argument\((.*?)\)", re.S)
CLICK_OPTION_CALL_RE = re.compile(r"(?:click\.option|typer\.Option)\((.*?)\)", re.S)
TYPER_OPTION_IMPORT_RE = re.compile(r"\bfrom\s+typer\s+import\b|\bimport\s+typer\b")
COMMAND_MODULE_RE = re.compile(r"module=['\"]([^'\"]+)['\"]")
DOMAIN_LIKE_RE = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/?$")
VERSION_LIKE_RE = re.compile(r"^\d+(?:\.\d+)+$")
ABBREVIATION_LIKE_RE = re.compile(r"^(?:[A-Z]\.)+[A-Z]?$")
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


def public_cli_surface_paths(root: Path) -> list[Path]:
    cli_modules: set[Path] = set()
    for cli_path in root.glob("src/**/cli.py"):
        text = read_text(cli_path)
        if "CommandSpec(" not in text:
            continue
        cli_modules.add(cli_path.resolve())
        for module_name in COMMAND_MODULE_RE.findall(text):
            module_path = root / "src" / Path(*module_name.split(".")).with_suffix(".py")
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

    for path in public_doc_surfaces(root):
        doc_path = root / path
        text = read_text(doc_path)
        candidates: list[tuple[str, int, int, bool]] = []
        candidates.extend(
            (match.group(1), match.start(1), match.end(1), True) for match in MARKDOWN_LINK_RE.finditer(text)
        )
        candidates.extend(
            (match.group(0), match.start(0), match.end(0), False) for match in PATH_TOKEN_RE.finditer(text)
        )
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
