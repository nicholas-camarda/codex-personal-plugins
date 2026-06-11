import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = ROOT / "plugins"


def load_module(name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_skill_description(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8")
    in_frontmatter = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


RESEARCH_PARTNER = load_module(
    "research_partner_script",
    "plugins/research-partner/scripts/research_partner.py",
)
WORKSPACE_GOVERNOR = load_module(
    "workspace_governor_script",
    "plugins/workspace-governor/scripts/workspace_governor.py",
)
DOCUMENTATION_WIZARD = load_module(
    "documentation_wizard_script",
    "plugins/documentation-wizard/scripts/documentation_wizard.py",
)
DEPLOY_PLUGINS = load_module(
    "deploy_plugins_script",
    "scripts/deploy_plugins.py",
)
FIXTURES_ROOT = ROOT / "tests" / "fixtures"


class PluginRegressionTests(unittest.TestCase):
    def stage_home_workspace(self, home_root: Path) -> Path:
        source_root = home_root / "source" / "codex-personal-plugins"
        source_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "plugins", source_root / "plugins")
        shutil.copytree(ROOT / "scripts", source_root / "scripts")
        shutil.copytree(ROOT / ".agents", source_root / ".agents")
        return source_root

    def install_plugins_for_test(self, home_root: Path) -> dict:
        source_root = self.stage_home_workspace(home_root)
        return DEPLOY_PLUGINS.install_plugins(
            source_root=source_root,
            home_root=home_root,
            run_validate=True,
        )

    def run_installed_plugin(self, home_root: Path, plugin_name: str, *args: str) -> dict:
        script_name = plugin_name.replace("-", "_") + ".py"
        script_path = home_root / ".codex" / "plugins" / plugin_name / "scripts" / script_name
        env = dict(os.environ)
        env["HOME"] = str(home_root)
        proc = subprocess.run(
            [sys.executable, str(script_path), *args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(proc.stdout)
        self.assertIsInstance(payload, dict)
        return payload

    def test_plugin_manifests_have_required_interface_urls(self) -> None:
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            manifest_path = PLUGINS_ROOT / plugin_name / ".codex-plugin" / "plugin.json"
            manifest = DEPLOY_PLUGINS.load_json(manifest_path)
            interface = manifest.get("interface", {})
            for key in ["websiteURL", "privacyPolicyURL", "termsOfServiceURL"]:
                value = interface.get(key)
                self.assertIsInstance(value, str, f"{plugin_name} missing interface.{key}")
                self.assertTrue(
                    value.startswith("https://github.com/nicholas-camarda/codex-personal-plugins"),
                    f"{plugin_name} has non-project URL for {key}",
                )
                self.assertNotIn("example.com", value)

    def test_skill_descriptions_use_clear_trigger_language(self) -> None:
        skill_paths = sorted(
            path
            for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]
            for path in (PLUGINS_ROOT / plugin_name / "skills").glob("*/SKILL.md")
        )
        self.assertGreater(len(skill_paths), 0)
        for skill_path in skill_paths:
            description = read_skill_description(skill_path)
            self.assertTrue(
                description.startswith("Use when "),
                f"{skill_path.relative_to(ROOT)} description should start with 'Use when '",
            )

    def test_research_partner_prefers_codex_plugins_root_for_peer_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            global_plugins_root = tmp / "global-plugins"
            peer_root = global_plugins_root / "workspace-governor"
            peer_root.mkdir(parents=True)

            with mock.patch.dict(
                os.environ,
                {"CODEX_PLUGINS_ROOT": str(global_plugins_root)},
                clear=False,
            ):
                resolved = RESEARCH_PARTNER.peer_plugin_root("workspace-governor")

        self.assertEqual(resolved, peer_root.resolve())

    def test_workspace_governor_falls_back_to_home_plugin_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            fake_current_root = tmp / "installed" / "workspace-governor"
            home_peer_root = fake_home / ".codex" / "plugins" / "documentation-wizard"
            fake_current_root.mkdir(parents=True)
            home_peer_root.mkdir(parents=True)

            with mock.patch.object(WORKSPACE_GOVERNOR, "CURRENT_PLUGIN_ROOT", fake_current_root):
                with mock.patch.object(WORKSPACE_GOVERNOR, "HOME", fake_home):
                    with mock.patch.dict(os.environ, {}, clear=True):
                        resolved = WORKSPACE_GOVERNOR._peer_plugin_root("documentation-wizard")

        self.assertEqual(resolved, home_peer_root.resolve())

    def test_parse_declared_path_finds_absolute_paths_inside_prose(self) -> None:
        line = (
            "Published artifacts are mirrored to "
            "`/Users/example/Library/CloudStorage/OneDrive-Personal/Research/project-alpha/results`, "
            "while runtime stays local."
        )

        resolved = RESEARCH_PARTNER.parse_declared_path(line)

        self.assertEqual(
            resolved,
            Path("/Users/example/Library/CloudStorage/OneDrive-Personal/Research/project-alpha/results"),
        )

    def test_inventory_repo_blocks_proceed_when_workspace_handoff_has_open_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "analysis-repo"
            repo_root.mkdir()
            (repo_root / "AGENTS.md").write_text("project_type: research\n", encoding="utf-8")
            (repo_root / "analysis_registry.yaml").write_text("project_type: research\n", encoding="utf-8")
            (repo_root / "scripts").mkdir()
            (repo_root / "scripts" / "analyze.py").write_text("print('ok')\n", encoding="utf-8")

            workspace_review = {
                "summary": RESEARCH_PARTNER.default_workspace_path_review("ok"),
                "status": "ok",
                "payload": {
                    "questions": ["Where should runtime artifacts live?"],
                    "doc_contract": {"passed": False},
                    "rewrite_candidates": [],
                },
            }

            with mock.patch.object(
                RESEARCH_PARTNER,
                "run_workspace_governor_dry_run",
                return_value=workspace_review,
            ):
                report = RESEARCH_PARTNER.inventory_repo(repo_root)

        self.assertNotIn("Proceed to specialist review lanes.", report["recommended_actions"])
        self.assertIn(
            "Review the workspace-governor dry-run questions before running specialist review lanes.",
            report["recommended_actions"],
        )
        finding_titles = {item["title"] for item in report["findings"]}
        self.assertIn("Workspace topology remains unresolved", finding_titles)
        self.assertIn("Public/private doc contract is incomplete", finding_titles)

    def test_publish_fails_before_copy_when_cloud_destination_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo_root = tmp / "analysis-repo"
            runtime_root = tmp / "runtime"
            cloud_home = tmp / "cloud-home"
            repo_root.mkdir()
            runtime_root.mkdir()
            cloud_home.mkdir()

            (repo_root / "README.md").write_text("# Analysis Repo\n", encoding="utf-8")
            (repo_root / "AGENTS.md").write_text(
                "\n".join(
                    [
                        "project_type: research",
                        f"runtime_home: {runtime_root}",
                        f"cloud_home: {cloud_home}",
                        "publish_layout: split-data-flat-analysis-v1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            source_path = runtime_root / "data" / "raw" / "season_datasets" / "slate.csv"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("season,player\n2026,test\n", encoding="utf-8")

            existing_destination = cloud_home / "data" / "raw" / "season_datasets" / "slate.csv"
            existing_destination.parent.mkdir(parents=True)
            existing_destination.write_text("season,player\n2025,existing\n", encoding="utf-8")

            args = argparse.Namespace(
                repo=str(repo_root),
                snapshot_id="snapshot-001",
                output=None,
                approve_doc_review=False,
            )

            with mock.patch.object(
                WORKSPACE_GOVERNOR,
                "doc_policy_report",
                return_value={
                    "report": {},
                    "sanitize_preview": {"changed_files": 0, "rewrites": [], "write": False},
                    "private_infra_findings": [],
                    "requires_rewrite": False,
                },
            ):
                payload = WORKSPACE_GOVERNOR.publish(args)

        self.assertEqual(payload["status"], "failed")
        self.assertIn("would be overwritten", payload["error"])
        checks = payload["publish_destination_checks"]
        self.assertEqual(checks["existing_destination_count"], 1)
        self.assertEqual(checks["duplicate_destination_count"], 0)

    def test_documentation_wizard_iter_files_prunes_non_public_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs" / "guide.md").parent.mkdir(parents=True)
            (root / "docs" / "guide.md").write_text("public\n", encoding="utf-8")
            (root / "docs" / "archive" / "old.md").parent.mkdir(parents=True)
            (root / "docs" / "archive" / "old.md").write_text("archived\n", encoding="utf-8")
            (root / "vendor" / "node_modules" / "pkg" / "readme.md").parent.mkdir(parents=True)
            (root / "vendor" / "node_modules" / "pkg" / "readme.md").write_text("ignored\n", encoding="utf-8")
            (root / ".history" / "notes.md").parent.mkdir(parents=True)
            (root / ".history" / "notes.md").write_text("hidden\n", encoding="utf-8")

            files = DOCUMENTATION_WIZARD.iter_files(root, {".md"})

        rel_paths = [path.relative_to(root).as_posix() for path in files]
        self.assertEqual(rel_paths, ["docs/guide.md"])

    def test_deploy_plugins_installs_home_marketplace_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home_root = Path(tmpdir) / "home"
            home_root.mkdir(parents=True)
            source_root = self.stage_home_workspace(home_root)

            payload = DEPLOY_PLUGINS.install_plugins(
                source_root=source_root,
                home_root=home_root,
                run_validate=True,
            )

            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["all_validations_passed"])
            home_marketplace = DEPLOY_PLUGINS.load_json(home_root / ".agents" / "plugins" / "marketplace.json")
            entry_names = [entry["name"] for entry in home_marketplace["plugins"]]
            self.assertEqual(entry_names, ["documentation-wizard", "research-partner", "workspace-governor"])
            for plugin_name in entry_names:
                install_root = home_root / ".codex" / "plugins" / plugin_name
                self.assertTrue((install_root / ".codex-plugin" / "plugin.json").exists())

    def test_documentation_wizard_report_smoke_on_generic_fixture(self) -> None:
        report = DOCUMENTATION_WIZARD.build_report(FIXTURES_ROOT / "generic_python_repo")

        self.assertEqual(report["scope"], "documentation-drift-audit")
        self.assertIsInstance(report["findings"], list)
        finding_kinds = {item["kind"] for item in report["findings"]}
        self.assertNotIn("stale-cli-flag", finding_kinds)
        self.assertNotIn("stale-config-key", finding_kinds)

    def test_workspace_governor_assess_smoke_on_research_fixture(self) -> None:
        repo_root = FIXTURES_ROOT / "research_repo"
        payload = WORKSPACE_GOVERNOR.assess(
            argparse.Namespace(
                repo=str(repo_root),
                classify=[],
                kind=None,
                roots=[str(FIXTURES_ROOT)],
                snapshot_id="smoke-001",
                output=None,
            )
        )

        self.assertEqual(payload["command"], "assess")
        self.assertEqual(payload["status"], "ok")
        self.assertIn("summary", payload)
        self.assertIn("assessment_outcome", payload["summary"])

    def test_research_partner_inventory_smoke_on_minimal_fixture(self) -> None:
        report = RESEARCH_PARTNER.inventory_repo(FIXTURES_ROOT / "minimal_repo")

        self.assertEqual(report["scope"], "analysis-review-preflight")
        self.assertIsInstance(report["findings"], list)
        self.assertIsInstance(report["recommended_actions"], list)
        self.assertIn("flow", report)

    def test_research_partner_run_executes_actual_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "review"
            report = RESEARCH_PARTNER.run_review(
                repo_root=FIXTURES_ROOT / "research_repo",
                output_dir=output_dir,
            )

            self.assertEqual(report["scope"], "multi-lane-review")
            self.assertEqual(report["command"], "run")
            self.assertEqual(report["status"], "ok")
            self.assertIn("lane_outputs", report)
            lane_names = {item["lane"] for item in report["lane_outputs"]}
            self.assertEqual(
                lane_names,
                {
                    "documentation-wizard",
                    "implementation-auditor",
                    "stats-reviewer",
                    "scientific-reviewer",
                    "literature-support-reviewer",
                    "robustness-test-designer",
                },
            )
            for lane in report["lane_outputs"]:
                path = Path(lane["path"])
                self.assertTrue(path.exists(), lane)
                payload = DEPLOY_PLUGINS.load_json(path)
                self.assertEqual(payload["lane"], lane["lane"])
                self.assertIn("artifact_map", payload)
                self.assertIn("findings", payload)
                self.assertIn("recommended_actions", payload)
            self.assertTrue((output_dir / "preflight.json").exists())
            self.assertTrue((output_dir / "bundle.json").exists())

    def test_research_partner_bundle_preserves_lane_provenance_for_same_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            preflight = tmp / "preflight.json"
            lane_one = tmp / "implementation.json"
            lane_two = tmp / "stats.json"
            preflight.write_text(
                json.dumps(
                    {
                        "scope": "analysis-review-preflight",
                        "artifact_map": {},
                        "findings": [],
                        "required_tests_checks": [],
                        "recommended_actions": [],
                    }
                ),
                encoding="utf-8",
            )
            lane_one.write_text(
                json.dumps(
                    {
                        "lane": "implementation-auditor",
                        "artifact_map": {},
                        "findings": [
                            {
                                "title": "Shared concern",
                                "severity": "P2",
                                "message": "Implementation message",
                                "lane": "implementation-auditor",
                            }
                        ],
                        "required_tests_checks": [],
                        "recommended_actions": [],
                    }
                ),
                encoding="utf-8",
            )
            lane_two.write_text(
                json.dumps(
                    {
                        "lane": "stats-reviewer",
                        "artifact_map": {},
                        "findings": [
                            {
                                "title": "Shared concern",
                                "severity": "P1",
                                "message": "Statistical message",
                                "lane": "stats-reviewer",
                            }
                        ],
                        "required_tests_checks": [],
                        "recommended_actions": [],
                    }
                ),
                encoding="utf-8",
            )

            bundle = RESEARCH_PARTNER.bundle_review(preflight, [lane_one, lane_two])

        shared = [finding for finding in bundle["findings"] if finding.get("title") == "Shared concern"]
        self.assertEqual(len(shared), 2)
        self.assertEqual({finding["lane"] for finding in shared}, {"implementation-auditor", "stats-reviewer"})

    def test_research_partner_keeps_generic_repo_topology_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "generic_python_repo"
            shutil.copytree(FIXTURES_ROOT / "generic_python_repo", repo_root)
            report = RESEARCH_PARTNER.inventory_repo(repo_root)

        workspace_review = report["artifact_map"]["workspace_path_review"]
        self.assertEqual(workspace_review["status"], "not-needed")
        self.assertEqual(workspace_review["source"], "generic-repo heuristic")
        self.assertEqual(workspace_review["topology_mode"], "generic-repo")
        self.assertEqual(workspace_review["topology_confidence"], "low")
        self.assertIsNone(workspace_review["proposed_code_root"])
        self.assertEqual(report["recommended_actions"], ["Proceed to specialist review lanes."])

    def test_workspace_governor_accepts_general_project_type_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "general-repo"
            repo_root.mkdir()
            (repo_root / "README.md").write_text("# General Repo\n", encoding="utf-8")
            (repo_root / "AGENTS.md").write_text("project_type: general\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname='general-repo'\n", encoding="utf-8")

            profile = WORKSPACE_GOVERNOR.infer_project_profile(repo_root, repo_root.name)
            dry_run = WORKSPACE_GOVERNOR.build_dry_run_plan(repo_root, profile)

        self.assertEqual(profile["profile_guess"], "general")
        self.assertTrue(profile["general_mode"])
        self.assertIsNone(dry_run["proposed_destination"])
        self.assertFalse(dry_run["doc_contract"]["required"])
        self.assertEqual(dry_run["doc_contract"]["message"], "Dual-doc contract is advisory for general software repos.")

    def test_documentation_wizard_extracts_click_and_typer_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "README.md").write_text("# CLI Fixture\n", encoding="utf-8")
            (repo_root / "scripts").mkdir()
            (repo_root / "scripts" / "click_cli.py").write_text(
                "\n".join(
                    [
                        "import click",
                        "",
                        "@click.command()",
                        "@click.option('--alpha', is_flag=True)",
                        "def main(alpha: bool) -> None:",
                        "    pass",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo_root / "scripts" / "typer_cli.py").write_text(
                "\n".join(
                    [
                        "import typer",
                        "",
                        "def main(beta: bool = typer.Option(False, '--beta')) -> None:",
                        "    pass",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            interfaces = DOCUMENTATION_WIZARD.extract_interfaces(repo_root)

        flags = {item["flag"] for item in interfaces["cli_flags"]}
        self.assertIn("--alpha", flags)
        self.assertIn("--beta", flags)

    def test_installed_documentation_wizard_executes_on_generic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home_root = Path(tmpdir) / "home"
            home_root.mkdir(parents=True)
            payload = self.install_plugins_for_test(home_root)
            self.assertEqual(payload["status"], "ok")

            report = self.run_installed_plugin(
                home_root,
                "documentation-wizard",
                "report",
                "--repo",
                str(FIXTURES_ROOT / "generic_python_repo"),
            )

        self.assertEqual(report["scope"], "documentation-drift-audit")
        finding_kinds = {item["kind"] for item in report["findings"]}
        self.assertNotIn("stale-cli-flag", finding_kinds)
        self.assertNotIn("stale-config-key", finding_kinds)

    def test_installed_research_partner_executes_on_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home_root = Path(tmpdir) / "home"
            home_root.mkdir(parents=True)
            payload = self.install_plugins_for_test(home_root)
            self.assertEqual(payload["status"], "ok")

            report = self.run_installed_plugin(
                home_root,
                "research-partner",
                "inventory",
                "--repo",
                str(FIXTURES_ROOT / "minimal_repo"),
            )

        self.assertEqual(report["scope"], "analysis-review-preflight")
        self.assertIn("flow", report)
        self.assertIsInstance(report["recommended_actions"], list)

    def test_installed_research_partner_run_executes_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home_root = tmp / "home"
            output_dir = tmp / "review"
            home_root.mkdir(parents=True)
            payload = self.install_plugins_for_test(home_root)
            self.assertEqual(payload["status"], "ok")

            report = self.run_installed_plugin(
                home_root,
                "research-partner",
                "run",
                "--repo",
                str(FIXTURES_ROOT / "research_repo"),
                "--output-dir",
                str(output_dir),
            )

        self.assertEqual(report["command"], "run")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["scope"], "multi-lane-review")
        self.assertEqual(len(report["lane_outputs"]), 6)

    def test_installed_workspace_governor_executes_on_research_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home_root = Path(tmpdir) / "home"
            home_root.mkdir(parents=True)
            payload = self.install_plugins_for_test(home_root)
            self.assertEqual(payload["status"], "ok")

            report = self.run_installed_plugin(
                home_root,
                "workspace-governor",
                "assess",
                "--repo",
                str(FIXTURES_ROOT / "research_repo"),
                "--roots",
                str(FIXTURES_ROOT),
                "--snapshot-id",
                "installed-smoke-001",
            )

        self.assertEqual(report["command"], "assess")
        self.assertEqual(report["status"], "ok")
        self.assertIn("summary", report)


if __name__ == "__main__":
    unittest.main()
