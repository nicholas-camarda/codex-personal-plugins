from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .classify import parse_classifications, parse_repo_kind
from .destination import child_dirs
from .git_io import write_json
from .metadata import infer_project_profile
from .paths import now_stamp
from .planning import build_audit_payload, build_dry_run_plan, classify_candidate
from .roots import DEFAULT_SCAN_ROOTS


def audit(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(root).expanduser().resolve() for root in (args.roots or [str(root) for root in DEFAULT_SCAN_ROOTS])]
    classifications = parse_classifications(args.classify or [])
    records: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            continue
        for child in child_dirs(root):
            records.append(classify_candidate(child, classifications))

    report = build_audit_payload(roots, classifications, records, now_stamp())
    if args.output:
        write_json(Path(args.output), report)
    return report


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")
    classifications = parse_classifications(args.classify or [])
    profile = infer_project_profile(repo_root, repo_root.name)
    if args.kind:
        profile["profile_guess"] = parse_repo_kind(args.kind)
    report = build_dry_run_plan(repo_root, profile, classifications)
    if args.output:
        write_json(Path(args.output), report)
    return report
