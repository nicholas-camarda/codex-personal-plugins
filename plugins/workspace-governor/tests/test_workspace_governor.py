import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]


def load_module():
    module_path = ROOT / "scripts" / "workspace_governor.py"
    spec = importlib.util.spec_from_file_location("workspace_governor_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["workspace_governor_local"] = module
    spec.loader.exec_module(module)
    return module


WORKSPACE_GOVERNOR = load_module()


class WorkspaceGovernorLocalTests(unittest.TestCase):
    def test_assess_smoke_on_research_fixture(self) -> None:
        fixtures_root = WORKSPACE_ROOT / "tests" / "fixtures"
        repo_root = fixtures_root / "research_repo"
        payload = WORKSPACE_GOVERNOR.assess(
            argparse.Namespace(
                repo=str(repo_root),
                classify=[],
                kind=None,
                roots=[str(fixtures_root)],
                snapshot_id="local-smoke-001",
                output=None,
            )
        )
        self.assertEqual(payload["command"], "assess")
        self.assertEqual(payload["status"], "ok")

    def test_split_layout_manifest_candidate_golden(self) -> None:
        candidate = WORKSPACE_GOVERNOR.map_publish_candidate(
            "data/raw/source_manifest.json",
            "split-data-flat-analysis-v1",
            2026,
        )
        self.assertEqual(candidate["destination_scope"], "cloud_home")
        self.assertEqual(candidate["destination_relative_path"], "data/raw/manifests/source_manifest_2026.json")


if __name__ == "__main__":
    unittest.main()
