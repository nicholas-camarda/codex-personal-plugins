import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
ROOT = WORKSPACE_ROOT / "plugins" / "workspace-governor"


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
    def test_dry_run_honors_existing_split_workspace_registry_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_home = Path(tmpdir) / "Workspaces" / "uveal-melanoma"
            repo_root = workspace_home / "source"
            repo_root.mkdir(parents=True)
            project_vault_home = (
                Path(tmpdir) / "Project Vault" / "Research" / "uveal-melanoma"
            )
            (repo_root / "README.md").write_text("# Uveal Melanoma\n", encoding="utf-8")
            (repo_root / "AGENTS.md").write_text("# Private path contract\n", encoding="utf-8")
            (repo_root / "analysis_registry.yaml").write_text(
                "\n".join(
                    [
                        "project_slug: uveal_melanoma",
                        "repository_slug: uveal-melanoma",
                        "project_type: research",
                        f"workspace_home: {workspace_home}",
                        f"source_home: {repo_root}",
                        f"runtime_home: {workspace_home / 'runtime'}",
                        f"results_home: {workspace_home / 'results'}",
                        f"project_vault_home: {project_vault_home}",
                        f"raw_home: {project_vault_home / 'Original Files'}",
                        f"publish_home: {project_vault_home / 'outputs'}",
                        "publish_root_name: outputs",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = WORKSPACE_GOVERNOR.infer_project_profile(repo_root, repo_root.name)
            dry_run = WORKSPACE_GOVERNOR.build_dry_run_plan(repo_root, profile)

        self.assertTrue(dry_run["registry_review"]["supported"])
        self.assertIsNone(dry_run["proposed_destination"])
        self.assertEqual(dry_run["proposed_code_root"], str(repo_root))
        self.assertEqual(dry_run["proposed_runtime_root"], str(workspace_home / "runtime"))
        self.assertEqual(dry_run["proposed_cloud_home"], str(project_vault_home))
        self.assertEqual(dry_run["questions"], [])

    def test_flat_workspace_repo_is_its_own_code_root(self) -> None:
        """The project folder is the Git repo; runtime/ sits inside it, with no source/ subfolder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_home = Path(tmpdir) / "Workspaces" / "flat-fixture"
            repo_root = workspace_home
            repo_root.mkdir(parents=True)
            project_vault_home = Path(tmpdir) / "Project Vault" / "Research" / "flat-fixture"
            (repo_root / "README.md").write_text("# Flat fixture\n", encoding="utf-8")
            (repo_root / "AGENTS.md").write_text("# Private path contract\n", encoding="utf-8")
            (repo_root / "analysis_registry.yaml").write_text(
                "\n".join(
                    [
                        "project_slug: flat-fixture",
                        "repository_slug: flat-fixture",
                        "project_type: research",
                        f"workspace_home: {workspace_home}",
                        f"project_vault_home: {project_vault_home}",
                        f"publish_home: {project_vault_home / 'outputs'}",
                        "publish_root_name: outputs",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            source_home, _ = WORKSPACE_GOVERNOR.configured_source_home(repo_root)
            profile = WORKSPACE_GOVERNOR.infer_project_profile(repo_root, repo_root.name)
            dry_run = WORKSPACE_GOVERNOR.build_dry_run_plan(repo_root, profile)

        self.assertEqual(source_home, workspace_home)
        self.assertIsNone(dry_run["proposed_destination"])
        self.assertEqual(dry_run["proposed_code_root"], str(repo_root))
        self.assertEqual(dry_run["proposed_runtime_root"], str(workspace_home / "runtime"))
        self.assertEqual(
            WORKSPACE_GOVERNOR.suggested_destination("flat-fixture", {"profile_guess": "research"}).name,
            "flat-fixture",
        )

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
