from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .lane_runners_documentation import run_documentation_wizard_lane
from .lane_runners_implementation import implementation_auditor_lane
from .lane_runners_literature import literature_support_lane
from .lane_runners_robustness import robustness_test_designer_lane
from .lane_runners_scientific import scientific_reviewer_lane
from .lane_runners_stats import stats_reviewer_lane


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def execute_lane(
    lane: str,
    root: Path,
    preflight: dict[str, Any],
    documentation_wizard_script: Path,
) -> dict[str, Any]:
    dispatch = {
        "documentation-wizard": lambda: run_documentation_wizard_lane(root, documentation_wizard_script),
        "implementation-auditor": lambda: implementation_auditor_lane(root, preflight),
        "stats-reviewer": lambda: stats_reviewer_lane(root, preflight),
        "scientific-reviewer": lambda: scientific_reviewer_lane(root, preflight),
        "literature-support-reviewer": lambda: literature_support_lane(root, preflight),
        "robustness-test-designer": lambda: robustness_test_designer_lane(root, preflight),
    }
    handler = dispatch.get(lane)
    if handler is None:
        raise ValueError(f"Unknown lane: {lane}")
    return handler()


def run_review(
    repo_root: Path,
    output_dir: Path,
    lanes: list[str] | None,
    *,
    executable_lanes: list[str],
    inventory_func,
    bundle_func,
    documentation_wizard_script: Path,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    selected_lanes = lanes or executable_lanes
    unknown = sorted(set(selected_lanes) - set(executable_lanes))
    if unknown:
        raise ValueError(f"Unknown lanes requested: {', '.join(unknown)}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = inventory_func(root)
    preflight_path = output_dir / "preflight.json"
    write_json(preflight_path, preflight)

    lane_paths: list[Path] = []
    lane_outputs: list[dict[str, Any]] = []
    for lane in selected_lanes:
        payload = execute_lane(lane, root, preflight, documentation_wizard_script)
        lane_path = output_dir / f"{lane}.json"
        write_json(lane_path, payload)
        lane_paths.append(lane_path)
        lane_outputs.append({"lane": lane, "path": str(lane_path), "finding_count": len(payload.get("findings", []))})

    bundle = bundle_func(preflight_path, lane_paths)
    bundle.update(
        {
            "command": "run",
            "status": "ok",
            "scope": "multi-lane-review",
            "repo_root": str(root),
            "output_dir": str(output_dir),
            "preflight_path": str(preflight_path),
            "lane_outputs": lane_outputs,
        }
    )
    bundle_path = output_dir / "bundle.json"
    write_json(bundle_path, bundle)
    bundle["bundle_path"] = str(bundle_path)
    return bundle
