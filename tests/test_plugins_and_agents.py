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

    def test_skills_are_compact_and_reference_detailed_policy_files(self) -> None:
        expectations = {
            "documentation-wizard": ["references/documentation-policy.md"],
            "research-partner": ["references/review-lanes.md"],
            "workspace-governor": ["references/workspace-policy.md"],
        }
        for plugin_name, reference_paths in expectations.items():
            plugin_root = PLUGINS_ROOT / plugin_name
            skill_files = sorted((plugin_root / "skills").glob("*/SKILL.md"))
            self.assertGreater(len(skill_files), 0)
            combined = "\n".join(path.read_text(encoding="utf-8") for path in skill_files)
            for reference_path in reference_paths:
                self.assertTrue((plugin_root / reference_path).exists(), reference_path)
                self.assertIn(reference_path, combined)
            for skill_file in skill_files:
                line_count = len(skill_file.read_text(encoding="utf-8").splitlines())
                self.assertLessEqual(line_count, 75, f"{skill_file.relative_to(ROOT)} is too long")

    def test_plugin_readmes_describe_repo_as_source_of_truth(self) -> None:
        forbidden_fragments = [
            "Keep the single source tree for this plugin at `~/.codex/plugins",
            "From the home plugin workspace root (`~/.codex/plugins`)",
            "does not copy plugins into a second location",
            "do not maintain a second repo-local plugin copy",
        ]
        required_fragments = [
            "This repository is the source of truth",
            "Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets",
            "python scripts/deploy_plugins.py install --source-root . --home ~",
        ]
        for readme_path in sorted(PLUGINS_ROOT.glob("*/README.md")):
            text = readme_path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, text, f"{readme_path.relative_to(ROOT)} contains stale source wording")
            for fragment in required_fragments:
                self.assertIn(fragment, text, f"{readme_path.relative_to(ROOT)} missing current source wording")

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

    def test_documentation_wizard_reports_stale_cli_flag_with_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "cli-doc-drift"
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "docs").mkdir()
            (repo_root / "README.md").write_text(
                "# CLI\n\nRun `python scripts/tool.py --old-flag`.\n",
                encoding="utf-8",
            )
            (repo_root / "scripts" / "tool.py").write_text(
                "\n".join(
                    [
                        "import argparse",
                        "parser = argparse.ArgumentParser()",
                        "parser.add_argument('--new-flag', action='store_true')",
                        "if __name__ == '__main__':",
                        "    parser.parse_args()",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = DOCUMENTATION_WIZARD.build_report(repo_root)

        stale_flags = [item for item in report["findings"] if item.get("kind") == "stale-cli-flag"]
        self.assertEqual(len(stale_flags), 1)
        self.assertEqual(stale_flags[0]["doc_ref"], "README.md:3")
        self.assertEqual(stale_flags[0]["source_ref"], "scripts/tool.py:3")
        self.assertIn("--old-flag", stale_flags[0]["message"])
        self.assertIn("--new-flag", stale_flags[0]["patch_direction"])

    def test_documentation_wizard_sanitize_public_docs_preserves_agents_path_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sanitize-fixture"
            repo_root.mkdir()
            public_path = repo_root / "README.md"
            agents_path = repo_root / "AGENTS.md"
            public_path.write_text(
                "Artifacts live at /Users/example/Library/CloudStorage/OneDrive-Personal/Research/project/output/result.csv\n",
                encoding="utf-8",
            )
            agents_path.write_text(
                "runtime_home: /Users/example/ProjectsRuntime/project\n",
                encoding="utf-8",
            )

            preview = DOCUMENTATION_WIZARD.sanitize_public_docs(repo_root, write=True)
            public_text = public_path.read_text(encoding="utf-8")
            agents_text = agents_path.read_text(encoding="utf-8")

        self.assertGreaterEqual(preview["changed_files"], 1)
        self.assertIn("output/result.csv", public_text)
        self.assertNotIn("/Users/example/Library/CloudStorage/OneDrive-Personal", public_text)
        self.assertIn("/Users/example/ProjectsRuntime/project", agents_text)

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

    def test_research_partner_single_lane_run_writes_only_requested_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "single-lane"
            report = RESEARCH_PARTNER.run_review(
                repo_root=FIXTURES_ROOT / "research_repo",
                output_dir=output_dir,
                lanes=["stats-reviewer"],
            )

            lane_outputs = report["lane_outputs"]
            self.assertEqual([item["lane"] for item in lane_outputs], ["stats-reviewer"])
            self.assertTrue((output_dir / "preflight.json").exists())
            self.assertTrue((output_dir / "stats-reviewer.json").exists())
            self.assertFalse((output_dir / "implementation-auditor.json").exists())
            self.assertTrue((output_dir / "bundle.json").exists())

    def test_research_partner_lane_findings_include_lane_and_evidence_basis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "review"
            report = RESEARCH_PARTNER.run_review(
                repo_root=FIXTURES_ROOT / "research_repo",
                output_dir=output_dir,
            )

            lane_findings = [finding for finding in report["findings"] if finding.get("lane")]
            self.assertGreater(len(lane_findings), 0)
            for finding in lane_findings:
                self.assertIsInstance(finding.get("lane"), str)
                self.assertIn(finding.get("evidence_basis"), {"Direct", "Inference", "Missing"})

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

    def test_workspace_governor_publish_candidate_split_layout_maps_manifest_with_year(self) -> None:
        candidate = WORKSPACE_GOVERNOR.map_publish_candidate(
            "data/raw/source_manifest.json",
            "split-data-flat-analysis-v1",
            2026,
        )

        self.assertEqual(
            candidate,
            {
                "destination_scope": "cloud_home",
                "destination_relative_path": "data/raw/manifests/source_manifest_2026.json",
            },
        )

    def test_workspace_governor_general_repo_assessment_has_no_move_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "general-tool"
            repo_root.mkdir()
            (repo_root / "README.md").write_text("# General Tool\n", encoding="utf-8")
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'general-tool'\n", encoding="utf-8")

            payload = WORKSPACE_GOVERNOR.assess(
                argparse.Namespace(
                    repo=str(repo_root),
                    classify=[],
                    kind=None,
                    roots=[str(repo_root.parent)],
                    snapshot_id="golden-001",
                    output=None,
                )
            )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["dry_run"]["profile_guess"], "general")
        self.assertEqual(payload["audit"]["plan"], [])

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


PLUGIN_EVAL_JS = Path(
    "/Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js"
)


class PluginEvalRegressionTests(unittest.TestCase):
    def test_plugin_eval_baseline_file_exists(self) -> None:
        baseline_path = ROOT / "tests" / "plugin_eval_baseline.json"
        self.assertTrue(baseline_path.exists(), "missing tests/plugin_eval_baseline.json")

    def test_plugin_python_heuristics_match_baseline_or_improve(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        baseline = json.loads((ROOT / "tests" / "plugin_eval_baseline.json").read_text(encoding="utf-8"))
        self.assertIn("plugins", baseline)
        for plugin_name, expected in baseline["plugins"].items():
            self.assertIn("max_complexity", expected, f"{plugin_name} baseline missing max_complexity")
            self.assertIn("long_lines", expected, f"{plugin_name} baseline missing long_lines")
            metrics = analyze_plugin_python(PLUGINS_ROOT / plugin_name / "scripts")
            self.assertLess(
                metrics["max_complexity"],
                18,
                f"{plugin_name} max complexity {metrics['max_complexity']} must be <18",
            )
            self.assertEqual(
                metrics["long_lines"],
                0,
                f"{plugin_name} has {metrics['long_lines']} lines >120 chars",
            )
            self.assertLessEqual(
                metrics["max_complexity"],
                expected["max_complexity"],
                f"{plugin_name} regressed on complexity",
            )
            self.assertEqual(
                metrics["long_lines"],
                expected["long_lines"],
                f"{plugin_name} long_lines regressed from baseline",
            )

    def test_plugin_python_has_no_lines_over_120_chars(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            metrics = analyze_plugin_python(PLUGINS_ROOT / plugin_name / "scripts")
            self.assertEqual(metrics["long_lines"], 0, plugin_name)

    def test_workspace_governor_plugin_eval_complexity_under_threshold(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        metrics = analyze_plugin_python(PLUGINS_ROOT / "workspace-governor" / "scripts")
        self.assertLess(metrics["max_complexity"], 18)
        worst = max(metrics["files"], key=lambda item: item["complexity"])
        self.assertLess(
            worst["complexity"],
            18,
            f"worst file {worst['path']} scored {worst['complexity']}",
        )

    def test_documentation_wizard_plugin_eval_complexity_under_threshold(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        metrics = analyze_plugin_python(PLUGINS_ROOT / "documentation-wizard" / "scripts")
        self.assertLess(metrics["max_complexity"], 18)

    def test_research_partner_plugin_eval_complexity_under_threshold(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        metrics = analyze_plugin_python(PLUGINS_ROOT / "research-partner" / "scripts")
        self.assertLess(metrics["max_complexity"], 18)

    def test_plugins_have_local_coverage_artifacts(self) -> None:
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            coverage_path = PLUGINS_ROOT / plugin_name / "coverage.xml"
            self.assertTrue(coverage_path.exists(), f"missing {coverage_path}")
            text = coverage_path.read_text(encoding="utf-8")
            self.assertIn("coverage", text)
            self.assertIn("line-rate", text)

    def test_plugins_have_no_cleared_warn_checks(self) -> None:
        if not PLUGIN_EVAL_JS.exists():
            self.skipTest("plugin-eval not installed")
        from scripts.plugin_eval_regression import run_plugin_eval_json

        cleared_warn_ids = {
            "py-complexity-high",
            "py-long-lines",
            "coverage-artifacts-unavailable",
        }
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            payload = run_plugin_eval_json(PLUGINS_ROOT / plugin_name, PLUGIN_EVAL_JS)
            warn_ids = {check["id"] for check in payload["checks"] if check.get("status") == "warn"}
            for warn_id in cleared_warn_ids:
                self.assertNotIn(
                    warn_id,
                    warn_ids,
                    f"{plugin_name} still warns on {warn_id}",
                )

    def test_research_partner_trigger_budget_is_not_heavy(self) -> None:
        if not PLUGIN_EVAL_JS.exists():
            self.skipTest("plugin-eval not installed")
        from scripts.plugin_eval_regression import run_plugin_eval_json

        payload = run_plugin_eval_json(PLUGINS_ROOT / "research-partner", PLUGIN_EVAL_JS)
        band = payload["budgets"]["trigger_cost_tokens"]["band"]
        self.assertIn(band, {"good", "moderate"}, f"trigger band is {band}")
        warn_ids = {check["id"] for check in payload["checks"] if check.get("status") == "warn"}
        self.assertNotIn("trigger_cost_tokens-budget-high", warn_ids)

    def test_deferred_token_budget_improved_from_baseline(self) -> None:
        if not PLUGIN_EVAL_JS.exists():
            self.skipTest("plugin-eval not installed")
        from scripts.plugin_eval_regression import run_plugin_eval_json

        baseline = json.loads((ROOT / "tests" / "plugin_eval_baseline.json").read_text(encoding="utf-8"))
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            payload = run_plugin_eval_json(PLUGINS_ROOT / plugin_name, PLUGIN_EVAL_JS)
            current = payload["budgets"]["deferred_cost_tokens"]["value"]
            previous = baseline["plugins"][plugin_name]["deferred_cost_tokens"]
            self.assertLessEqual(
                current,
                previous,
                f"{plugin_name} deferred tokens {current} regressed from baseline {previous}",
            )


if __name__ == "__main__":
    unittest.main()
