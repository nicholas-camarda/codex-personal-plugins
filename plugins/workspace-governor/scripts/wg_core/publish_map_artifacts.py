from __future__ import annotations

from pathlib import PurePosixPath


def map_run_artifacts(
    parts: tuple[str, ...],
    latest_run_year: int,
) -> dict[str, str] | None:
    run_prefix = ("runs", str(latest_run_year), "pre_draft")

    if parts[:5] == run_prefix + ("artifacts", "draft_strategy"):
        rest = parts[5:]
        if not rest:
            return None
        relative_rest = PurePosixPath(*rest)
        if relative_rest.match("finalized_drafts/*_test.*"):
            return None
        if relative_rest.name == f"draft_board_{latest_run_year}.html":
            return {"destination_scope": "snapshot", "destination_relative_path": "dashboard/index.html"}
        if relative_rest.name == f"draft_board_{latest_run_year}.json":
            return None
        if relative_rest.name == f"dashboard_payload_{latest_run_year}.json":
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": "dashboard/dashboard_payload.json",
            }
        return {
            "destination_scope": "snapshot",
            "destination_relative_path": f"draft_strategy/{relative_rest.as_posix()}",
        }

    artifact_maps = [
        (run_prefix + ("artifacts", "hybrid_mc_bayesian"), "hybrid_mc_bayesian"),
        (run_prefix + ("artifacts", "vor_strategy"), "vor_strategy"),
        (run_prefix + ("diagnostics",), "diagnostics"),
    ]
    for prefix, label in artifact_maps:
        if parts[: len(prefix)] == prefix:
            rest = PurePosixPath(*parts[len(prefix) :])
            if not rest.parts:
                return None
            return {
                "destination_scope": "snapshot",
                "destination_relative_path": f"{label}/{rest.as_posix()}",
            }

    return None
