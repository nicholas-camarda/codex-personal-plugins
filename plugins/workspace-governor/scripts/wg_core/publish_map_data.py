from __future__ import annotations

from pathlib import PurePosixPath


def map_data_paths(path_obj: PurePosixPath, latest_run_year: int | None) -> dict[str, str] | None:
    parts = path_obj.parts
    year_suffix = str(latest_run_year) if latest_run_year is not None else "current"

    if parts[:3] == ("data", "raw", "season_datasets") and path_obj.suffix == ".csv":
        return {"destination_scope": "cloud_home", "destination_relative_path": path_obj.as_posix()}

    if parts[:2] == ("data", "raw") and len(parts) == 3 and path_obj.suffix == ".json":
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/raw/manifests/{path_obj.stem}_{year_suffix}{path_obj.suffix}"
            ),
        }

    if parts[:3] == ("data", "processed", "combined_datasets") and path_obj.name.endswith("season_modern.csv"):
        return {"destination_scope": "cloud_home", "destination_relative_path": path_obj.as_posix()}

    if parts[:3] == ("data", "processed", "snake_draft_datasets") and len(parts) >= 4:
        return {"destination_scope": "cloud_home", "destination_relative_path": path_obj.as_posix()}

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.csv"):
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.csv"
            ),
        }

    if parts == ("data", "processed", "unified_dataset", "unified_dataset.json"):
        return {
            "destination_scope": "cloud_home",
            "destination_relative_path": (
                f"data/processed/unified_dataset/unified_dataset_{year_suffix}.json"
            ),
        }

    return None
