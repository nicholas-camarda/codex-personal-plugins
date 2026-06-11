# Plugin Efficiency And Quality Follow-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `documentation-wizard`, `research-partner`, and `workspace-governor` easier to maintain, cheaper to invoke, and more behaviorally reliable without changing their public CLI contracts.

**Architecture:** First remove documentation drift and add golden behavioral tests so refactors have a safety net. Then extract focused helper modules from the large single-file scripts while keeping the existing CLI entrypoint filenames intact. Finally reduce skill token cost by moving detailed guidance into references, add coverage artifacts, and rerun Plugin Eval.

**Tech Stack:** Python 3 standard library, `unittest`, `coverage` if available, JSON fixture assertions, local Codex plugin manifests, Plugin Eval CLI via `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js`.

---

## Scope

This plan covers one follow-up quality pass across the three plugins:

- fix stale plugin-level README source/deploy wording
- add golden behavioral tests before refactoring
- split the largest helper scripts into focused local modules
- move verbose skill guidance into `references/` files to lower deferred token cost
- add coverage artifact generation
- rerun validation and Plugin Eval

This plan does not change plugin names, manifest paths, marketplace layout, or installed-copy deployment semantics. Do not add fallback paths, silent degradation, compatibility shims, or duplicate CLI implementations.

## Current Evidence

Fresh local inspection before this plan:

- `plugins/documentation-wizard/scripts/documentation_wizard.py`: 913 lines
- `plugins/research-partner/scripts/research_partner.py`: 880 lines
- `plugins/workspace-governor/scripts/workspace_governor.py`: 2027 lines
- Plugin Eval warnings:
  - documentation-wizard: deferred token cost, Python complexity, long lines
  - research-partner: trigger/invoke/deferred token cost, Python complexity, long lines
  - workspace-governor: deferred token cost, Python complexity, long lines
- plugin-level READMEs still describe `~/.codex/plugins` as the single source tree; current source of truth is this repo under `plugins/<plugin-name>/`.

## File Structure

Create:

- `plugins/documentation-wizard/scripts/dw_core/__init__.py`
- `plugins/documentation-wizard/scripts/dw_core/files.py`
- `plugins/documentation-wizard/scripts/dw_core/interfaces.py`
- `plugins/documentation-wizard/scripts/dw_core/reporting.py`
- `plugins/documentation-wizard/scripts/dw_core/sanitize.py`
- `plugins/research-partner/scripts/rp_core/__init__.py`
- `plugins/research-partner/scripts/rp_core/lanes.py`
- `plugins/research-partner/scripts/rp_core/bundles.py`
- `plugins/research-partner/scripts/rp_core/workspace.py`
- `plugins/workspace-governor/scripts/wg_core/__init__.py`
- `plugins/workspace-governor/scripts/wg_core/metadata.py`
- `plugins/workspace-governor/scripts/wg_core/publish.py`
- `plugins/workspace-governor/scripts/wg_core/planning.py`
- `plugins/workspace-governor/scripts/wg_core/verification.py`
- `plugins/documentation-wizard/references/documentation-policy.md`
- `plugins/research-partner/references/review-lanes.md`
- `plugins/workspace-governor/references/workspace-policy.md`
- `.coveragerc`
- `docs/superpowers/plans/2026-06-11-plugin-efficiency-quality-followup-results.md`

Modify:

- `plugins/documentation-wizard/README.md`
- `plugins/research-partner/README.md`
- `plugins/workspace-governor/README.md`
- `plugins/documentation-wizard/skills/documentation-wizard/SKILL.md`
- `plugins/research-partner/skills/research-partner/SKILL.md`
- `plugins/research-partner/skills/review-documentation-consistency/SKILL.md`
- `plugins/research-partner/skills/review-implementation-validity/SKILL.md`
- `plugins/research-partner/skills/review-scientific-interpretation/SKILL.md`
- `plugins/research-partner/skills/review-statistical-validity/SKILL.md`
- `plugins/research-partner/skills/assess-literature-support/SKILL.md`
- `plugins/research-partner/skills/design-robustness-tests/SKILL.md`
- `plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md`
- `plugins/research-partner/skills/synthesize-review/SKILL.md`
- `plugins/workspace-governor/skills/workspace-governor/SKILL.md`
- `plugins/documentation-wizard/scripts/documentation_wizard.py`
- `plugins/research-partner/scripts/research_partner.py`
- `plugins/workspace-governor/scripts/workspace_governor.py`
- `tests/test_plugins_and_agents.py`
- `plugins/documentation-wizard/tests/test_documentation_wizard.py`
- `plugins/research-partner/tests/test_research_partner.py`
- `plugins/workspace-governor/tests/test_workspace_governor.py`
- `README.md`

Do not modify:

- `.agents/plugins/marketplace.json`
- plugin names in `.codex-plugin/plugin.json`
- helper script filenames used by manifests and tests

---

### Task 1: Fix Plugin-Level README Drift

**Files:**
- Modify: `plugins/documentation-wizard/README.md`
- Modify: `plugins/research-partner/README.md`
- Modify: `plugins/workspace-governor/README.md`
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add failing README source-of-truth test**

Add this method inside `PluginRegressionTests` in `tests/test_plugins_and_agents.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_plugin_readmes_describe_repo_as_source_of_truth -v
```

Expected: FAIL because plugin-level READMEs still say `~/.codex/plugins` is the single source tree.

- [ ] **Step 3: Replace documentation-wizard README deployment text**

In `plugins/documentation-wizard/README.md`, replace the two paragraphs after the helper command list:

```markdown
`validate` confirms the home plugin bundle is in place.
Keep the single source tree for this plugin at `~/.codex/plugins/documentation-wizard`.
Use the personal marketplace at `~/.agents/plugins/marketplace.json`; do not maintain a second repo-local plugin copy.

## Deployment

From the home plugin workspace root (`~/.codex/plugins`), run `python3 scripts/deploy_plugins.py install` to refresh the personal marketplace manifest under `~/.agents/plugins/marketplace.json`. This workflow keeps `~/.codex/plugins` as the only source tree and does not copy plugins into a second location.
```

with:

````markdown
`validate` confirms the plugin bundle is registered and its manifest, skill, and assets are present.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

From the repository root, run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

The deploy script copies this plugin into `~/.codex/plugins/documentation-wizard` and refreshes the personal marketplace at `~/.agents/plugins/marketplace.json`.
````

- [ ] **Step 4: Replace research-partner README helper and deployment section**

In `plugins/research-partner/README.md`, replace the helper command list:

```markdown
- `inventory --repo <path>`
- `bundle --preflight <json> --lane <json> [...]`
- `validate`
```

with:

```markdown
- `inventory --repo <path>`
- `run --repo <path> --output-dir <dir> [--lane <name>]`
- `bundle --preflight <json> --lane <json> [...]`
- `validate`
```

Then replace the stale source/deployment paragraphs with:

````markdown
`validate` confirms the plugin bundle is registered and its manifest, skills, dependencies, and assets are present.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

From the repository root, run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

The deploy script copies this plugin into `~/.codex/plugins/research-partner` and refreshes the personal marketplace at `~/.agents/plugins/marketplace.json`.
````

- [ ] **Step 5: Replace workspace-governor README validation and deployment section**

In `plugins/workspace-governor/README.md`, replace:

```markdown
Run `scripts/workspace_governor.py validate` to confirm the home plugin bundle is in place.
Keep the single source tree for this plugin at `~/.codex/plugins/workspace-governor`.
Use the personal marketplace at `~/.agents/plugins/marketplace.json`; do not maintain a second repo-local plugin copy.

## Deployment

From the home plugin workspace root (`~/.codex/plugins`), run `python3 scripts/deploy_plugins.py install` to refresh the personal marketplace manifest under `~/.agents/plugins/marketplace.json`. This workflow keeps `~/.codex/plugins` as the only source tree and does not copy plugins into a second location.
```

with:

````markdown
Run `scripts/workspace_governor.py validate` to confirm the plugin bundle is registered and its manifest, skill, dependencies, and assets are present.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

From the repository root, run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

The deploy script copies this plugin into `~/.codex/plugins/workspace-governor` and refreshes the personal marketplace at `~/.agents/plugins/marketplace.json`.
````

- [ ] **Step 6: Run README test**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_plugin_readmes_describe_repo_as_source_of_truth -v
```

Expected: PASS.

- [ ] **Step 7: Run root suite**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add tests/test_plugins_and_agents.py plugins/documentation-wizard/README.md plugins/research-partner/README.md plugins/workspace-governor/README.md
git commit -m "docs: align plugin readmes with source repo layout"
```

---

### Task 2: Add Golden Behavioral Tests Before Refactors

**Files:**
- Modify: `tests/test_plugins_and_agents.py`
- Modify: `plugins/documentation-wizard/tests/test_documentation_wizard.py`
- Modify: `plugins/research-partner/tests/test_research_partner.py`
- Modify: `plugins/workspace-governor/tests/test_workspace_governor.py`

- [ ] **Step 1: Add documentation-wizard golden tests**

Add these methods inside `PluginRegressionTests` in `tests/test_plugins_and_agents.py`:

```python
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
        self.assertIn("--old-flag", stale_flags[0]["message"])
        self.assertIn("--new-flag", json.dumps(report["artifact_map"]))

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

        self.assertGreaterEqual(preview["changed_files"], 1)
        self.assertIn("output/result.csv", public_path.read_text(encoding="utf-8"))
        self.assertIn("/Users/example/ProjectsRuntime/project", agents_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Add research-partner golden tests**

Add these methods inside `PluginRegressionTests`:

```python
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
```

- [ ] **Step 3: Add workspace-governor golden tests**

Add these methods inside `PluginRegressionTests`:

```python
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
        self.assertEqual(payload["summary"]["profile_guess"], "general")
        self.assertEqual(payload["dry_run"]["move_plan"], [])
```

- [ ] **Step 4: Mirror high-value golden tests into plugin-local suites**

In `plugins/documentation-wizard/tests/test_documentation_wizard.py`, add:

```python
    def test_stale_cli_flag_golden(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "cli-doc-drift"
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "README.md").write_text(
                "# CLI\n\nRun `python scripts/tool.py --old-flag`.\n",
                encoding="utf-8",
            )
            (repo_root / "scripts" / "tool.py").write_text(
                "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--new-flag')\n",
                encoding="utf-8",
            )
            report = DOCUMENTATION_WIZARD.build_report(repo_root)
        self.assertEqual([item["kind"] for item in report["findings"]], ["stale-cli-flag"])
```

In `plugins/research-partner/tests/test_research_partner.py`, add:

```python
    def test_single_lane_run_executes_only_requested_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "single-lane"
            report = RESEARCH_PARTNER.run_review(
                WORKSPACE_ROOT / "tests" / "fixtures" / "research_repo",
                output_dir,
                lanes=["stats-reviewer"],
            )
        self.assertEqual([item["lane"] for item in report["lane_outputs"]], ["stats-reviewer"])
```

In `plugins/workspace-governor/tests/test_workspace_governor.py`, add:

```python
    def test_split_layout_manifest_candidate_golden(self) -> None:
        candidate = WORKSPACE_GOVERNOR.map_publish_candidate(
            "data/raw/source_manifest.json",
            "split-data-flat-analysis-v1",
            2026,
        )
        self.assertEqual(candidate["destination_scope"], "cloud_home")
        self.assertEqual(candidate["destination_relative_path"], "data/raw/manifests/source_manifest_2026.json")
```

- [ ] **Step 5: Run golden tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: PASS. If a golden test fails because current behavior differs, inspect the concrete output. Either adjust the test if the current behavior is scientifically or operationally correct, or fix the behavior in the smallest matching script function.

- [ ] **Step 6: Commit**

Run:

```bash
git add tests/test_plugins_and_agents.py plugins/documentation-wizard/tests/test_documentation_wizard.py plugins/research-partner/tests/test_research_partner.py plugins/workspace-governor/tests/test_workspace_governor.py
git commit -m "test: add plugin behavioral golden tests"
```

---

### Task 3: Extract Documentation Wizard Core Modules

**Files:**
- Create: `plugins/documentation-wizard/scripts/dw_core/__init__.py`
- Create: `plugins/documentation-wizard/scripts/dw_core/files.py`
- Create: `plugins/documentation-wizard/scripts/dw_core/interfaces.py`
- Create: `plugins/documentation-wizard/scripts/dw_core/reporting.py`
- Create: `plugins/documentation-wizard/scripts/dw_core/sanitize.py`
- Modify: `plugins/documentation-wizard/scripts/documentation_wizard.py`

- [ ] **Step 1: Create empty package marker**

Create `plugins/documentation-wizard/scripts/dw_core/__init__.py`:

```python
"""Focused helpers for documentation_wizard.py."""
```

- [ ] **Step 2: Extract file walking helpers**

Move these definitions unchanged from `documentation_wizard.py` into `plugins/documentation-wizard/scripts/dw_core/files.py`:

```python
from __future__ import annotations

import os
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".history",
    ".codex",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "archive",
    "archived",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def iter_files(root: Path, suffixes: set[str]) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and name.lower() not in IGNORED_DIRS
        ]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() in suffixes:
                paths.append(path)
    return sorted(paths)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
```

In `documentation_wizard.py`, replace the original definitions with:

```python
from dw_core.files import IGNORED_DIRS, iter_files, read_text, relative
```

Remove now-unused `import os` only if no remaining code in `documentation_wizard.py` uses `os`.

- [ ] **Step 3: Run focused docs tests**

Run:

```bash
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_documentation_wizard_iter_files_prunes_non_public_directories -v
```

Expected: PASS.

- [ ] **Step 4: Extract interface extraction helpers**

Move these definitions and their required regex constants from `documentation_wizard.py` into `plugins/documentation-wizard/scripts/dw_core/interfaces.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .files import iter_files, read_text, relative
```

Move the current implementations unchanged for:

- `public_cli_surface_paths`
- `extract_cli_flags`
- `walk_schema`
- `extract_interfaces`

Also move only the constants those functions directly use, including:

- `ARGPARSE_CALL_RE`
- `CLICK_OPTION_CALL_RE`
- `TYPER_OPTION_IMPORT_RE`
- `FLAG_RE`
- `MARKDOWN_LINK_RE`
- `PATH_TOKEN_RE`
- `PATH_CONTINUATION_CHARS`
- `DOC_SUFFIXES` if still directly needed

In `documentation_wizard.py`, import:

```python
from dw_core.interfaces import extract_cli_flags, extract_interfaces, public_cli_surface_paths, walk_schema
```

- [ ] **Step 5: Run interface tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_documentation_wizard_extracts_click_and_typer_flags -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_documentation_wizard_reports_stale_cli_flag_with_source_refs -v
```

Expected: PASS.

- [ ] **Step 6: Extract sanitization helpers**

Move these definitions and their required constants into `plugins/documentation-wizard/scripts/dw_core/sanitize.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .files import read_text
```

Move current implementations unchanged for:

- `InfraPattern`
- `portable_suffix_after`
- `portable_public_replacement`
- `replacement_for_match`
- `find_private_infra_leaks`
- `sanitize_public_docs`

In `documentation_wizard.py`, import:

```python
from dw_core.sanitize import (
    InfraPattern,
    find_private_infra_leaks,
    portable_public_replacement,
    portable_suffix_after,
    replacement_for_match,
    sanitize_public_docs,
)
```

- [ ] **Step 7: Run sanitization tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_documentation_wizard_sanitize_public_docs_preserves_agents_path_truth -v
python -m unittest discover -s plugins/documentation-wizard/tests -v
```

Expected: PASS.

- [ ] **Step 8: Extract reporting helpers**

Move these definitions and their required constants into `plugins/documentation-wizard/scripts/dw_core/reporting.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .files import iter_files, read_text, relative
from .interfaces import extract_interfaces
from .sanitize import find_private_infra_leaks, sanitize_public_docs
```

Move current implementations unchanged for:

- `analysis_registry_review`
- `inventory_docs`
- `build_report`
- `build_regression_check`

In `documentation_wizard.py`, import:

```python
from dw_core.reporting import analysis_registry_review, build_regression_check, build_report, inventory_docs
```

- [ ] **Step 9: Run full documentation-wizard gate**

Run:

```bash
python -m unittest discover -s plugins/documentation-wizard/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/documentation-wizard/scripts/documentation_wizard.py report --repo tests/fixtures/generic_python_repo
python -m unittest tests/test_plugins_and_agents.py
```

Expected: PASS and JSON output for `report`.

- [ ] **Step 10: Commit**

Run:

```bash
git add plugins/documentation-wizard/scripts/documentation_wizard.py plugins/documentation-wizard/scripts/dw_core tests plugins/documentation-wizard/tests
git commit -m "refactor: split documentation wizard helpers"
```

---

### Task 4: Extract Research Partner Core Modules

**Files:**
- Create: `plugins/research-partner/scripts/rp_core/__init__.py`
- Create: `plugins/research-partner/scripts/rp_core/workspace.py`
- Create: `plugins/research-partner/scripts/rp_core/lanes.py`
- Create: `plugins/research-partner/scripts/rp_core/bundles.py`
- Modify: `plugins/research-partner/scripts/research_partner.py`

- [ ] **Step 1: Create empty package marker**

Create `plugins/research-partner/scripts/rp_core/__init__.py`:

```python
"""Focused helpers for research_partner.py."""
```

- [ ] **Step 2: Extract workspace path review helpers**

Move these definitions and required constants into `plugins/research-partner/scripts/rp_core/workspace.py`:

```python
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
```

Move current implementations unchanged for:

- `read_text`
- `is_relative_to`
- `parse_declared_path`
- `default_workspace_path_review`
- `classify_workspace_topology`
- `run_workspace_governor_dry_run`
- `append_workspace_findings`

Keep `peer_plugin_root` and `peer_plugin_script` in `research_partner.py` for now, and pass `workspace_governor_script` into `run_workspace_governor_dry_run`.

Use this signature in the extracted module:

```python
def run_workspace_governor_dry_run(root: Path, workspace_governor_script: Path) -> dict[str, Any]:
```

Update the call in `inventory_repo()`:

```python
workspace_review = run_workspace_governor_dry_run(root, WORKSPACE_GOVERNOR_SCRIPT)
```

- [ ] **Step 3: Run workspace-preflight tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_parse_declared_path_finds_absolute_paths_inside_prose -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_inventory_repo_blocks_proceed_when_workspace_handoff_has_open_questions -v
```

Expected: PASS.

- [ ] **Step 4: Extract lane execution helpers**

Move these definitions into `plugins/research-partner/scripts/rp_core/lanes.py`:

```python
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
```

Move current implementations unchanged for:

- `write_json`
- `lane_payload`
- `_repo_files`
- `run_documentation_wizard_lane`
- `implementation_auditor_lane`
- `stats_reviewer_lane`
- `scientific_reviewer_lane`
- `literature_support_lane`
- `robustness_test_designer_lane`
- `execute_lane`
- `run_review`

Use dependency injection for peer documentation script and bundle function:

```python
def run_documentation_wizard_lane(root: Path, documentation_wizard_script: Path) -> dict[str, Any]:
```

```python
def execute_lane(
    lane: str,
    root: Path,
    preflight: dict[str, Any],
    documentation_wizard_script: Path,
) -> dict[str, Any]:
```

```python
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
```

In `research_partner.py`, wrap the extracted implementation with the existing public signature:

```python
from rp_core.lanes import run_review as run_review_impl


def run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None) -> dict[str, Any]:
    return run_review_impl(
        repo_root,
        output_dir,
        lanes,
        executable_lanes=EXECUTABLE_LANES,
        inventory_func=inventory_repo,
        bundle_func=bundle_review,
        documentation_wizard_script=peer_plugin_script("documentation-wizard", "documentation_wizard.py"),
    )
```

- [ ] **Step 5: Run lane tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_run_executes_actual_lanes -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_single_lane_run_writes_only_requested_lane -v
python -m unittest discover -s plugins/research-partner/tests -v
```

Expected: PASS.

- [ ] **Step 6: Extract bundling helpers**

Move these definitions into `plugins/research-partner/scripts/rp_core/bundles.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .lanes import write_json
```

Move current implementations unchanged for:

- `load_json`
- `finding_key`
- `bundle_review`

Keep a compatibility import in `research_partner.py`:

```python
from rp_core.bundles import bundle_review, finding_key, load_json
```

- [ ] **Step 7: Run bundle tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_bundle_preserves_lane_provenance_for_same_title -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_lane_findings_include_lane_and_evidence_basis -v
python -m unittest tests/test_plugins_and_agents.py
```

Expected: PASS.

- [ ] **Step 8: Run full research-partner gate**

Run:

```bash
python -m unittest discover -s plugins/research-partner/tests -v
python plugins/research-partner/scripts/research_partner.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-refactor-smoke
python -m unittest tests/test_plugins_and_agents.py
```

Expected: PASS and `run` emits JSON with `"status": "ok"`.

- [ ] **Step 9: Commit**

Run:

```bash
git add plugins/research-partner/scripts/research_partner.py plugins/research-partner/scripts/rp_core tests plugins/research-partner/tests
git commit -m "refactor: split research partner helpers"
```

---

### Task 5: Extract Workspace Governor Core Modules

**Files:**
- Create: `plugins/workspace-governor/scripts/wg_core/__init__.py`
- Create: `plugins/workspace-governor/scripts/wg_core/metadata.py`
- Create: `plugins/workspace-governor/scripts/wg_core/publish.py`
- Create: `plugins/workspace-governor/scripts/wg_core/planning.py`
- Create: `plugins/workspace-governor/scripts/wg_core/verification.py`
- Modify: `plugins/workspace-governor/scripts/workspace_governor.py`

- [ ] **Step 1: Create empty package marker**

Create `plugins/workspace-governor/scripts/wg_core/__init__.py`:

```python
"""Focused helpers for workspace_governor.py."""
```

- [ ] **Step 2: Extract metadata parsing helpers**

Move these definitions and required constants into `plugins/workspace-governor/scripts/wg_core/metadata.py`:

```python
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
```

Move current implementations unchanged for:

- `load_text`
- `parse_metadata_text`
- `infer_project_profile`

Keep public wrapper imports in `workspace_governor.py`:

```python
from wg_core.metadata import infer_project_profile, load_text, parse_metadata_text
```

- [ ] **Step 3: Run metadata tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_accepts_general_project_type_metadata -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_general_repo_assessment_has_no_move_plan -v
```

Expected: PASS.

- [ ] **Step 4: Extract publish mapping helpers**

Move these definitions and required constants into `plugins/workspace-governor/scripts/wg_core/publish.py`:

```python
from __future__ import annotations

import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any
```

Move current implementations unchanged for:

- `path_denied`
- `detect_latest_run_year`
- `map_publish_candidate`
- `iter_publish_candidates`
- `build_publish_report`

Keep public wrapper imports in `workspace_governor.py`:

```python
from wg_core.publish import (
    build_publish_report,
    detect_latest_run_year,
    iter_publish_candidates,
    map_publish_candidate,
    path_denied,
)
```

- [ ] **Step 5: Run publish mapping tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_publish_candidate_split_layout_maps_manifest_with_year -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_publish_fails_before_copy_when_cloud_destination_exists -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: PASS.

- [ ] **Step 6: Extract planning helpers**

Move these definitions and required constants into `plugins/workspace-governor/scripts/wg_core/planning.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any
```

Move current implementations unchanged for:

- `build_dry_run_plan`
- `classify_candidate`
- `build_audit_payload`

Keep wrappers in `workspace_governor.py`:

```python
from wg_core.planning import build_audit_payload, build_dry_run_plan, classify_candidate
```

- [ ] **Step 7: Run planning tests**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_installed_workspace_governor_executes_on_research_fixture -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: PASS.

- [ ] **Step 8: Extract verification helpers**

Move these definitions and required constants into `plugins/workspace-governor/scripts/wg_core/verification.py`:

```python
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
```

Move current implementations unchanged for:

- `file_digest`
- `copytree_verified`
- `apply_one`
- `apply_plan`
- `verify_manifest`

Keep wrappers in `workspace_governor.py`:

```python
from wg_core.verification import apply_one, apply_plan, copytree_verified, file_digest, verify_manifest
```

- [ ] **Step 9: Run full workspace-governor gate**

Run:

```bash
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/workspace-governor/scripts/workspace_governor.py assess --repo tests/fixtures/research_repo --roots tests/fixtures --snapshot-id refactor-smoke
python -m unittest tests/test_plugins_and_agents.py
```

Expected: PASS and `assess` emits JSON with `"status": "ok"`.

- [ ] **Step 10: Commit**

Run:

```bash
git add plugins/workspace-governor/scripts/workspace_governor.py plugins/workspace-governor/scripts/wg_core tests plugins/workspace-governor/tests
git commit -m "refactor: split workspace governor helpers"
```

---

### Task 6: Reduce Skill Token Cost With Reference Files

**Files:**
- Create: `plugins/documentation-wizard/references/documentation-policy.md`
- Create: `plugins/research-partner/references/review-lanes.md`
- Create: `plugins/workspace-governor/references/workspace-policy.md`
- Modify: `plugins/documentation-wizard/skills/documentation-wizard/SKILL.md`
- Modify: all `plugins/research-partner/skills/*/SKILL.md`
- Modify: `plugins/workspace-governor/skills/workspace-governor/SKILL.md`
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add reference-link regression test**

Add this method inside `PluginRegressionTests`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_skills_are_compact_and_reference_detailed_policy_files -v
```

Expected: FAIL because references do not exist and some skills exceed 75 lines.

- [ ] **Step 3: Create documentation policy reference**

Create `plugins/documentation-wizard/references/documentation-policy.md`:

```markdown
# Documentation Policy

Use this reference when documentation review requires more detail than the skill entrypoint contains.

## Source-Of-Truth Order

1. parser, schema, or CLI help output
2. generated docs when generation is canonical
3. maintained prose docs such as `README*` and `docs/`

Public docs should remain portable. Maintainer-specific infrastructure such as `OneDrive`, `~/ProjectsRuntime`, and `/Users/...` belongs in `AGENTS.md` or clearly internal docs such as `.local.md`.

## Helper Commands

- `inventory --repo <path>`
- `interfaces --repo <path>`
- `report --repo <path>`
- `regression-check --repo <path> --kind <cli-flags|config-schema|referenced-paths|private-infra>`
- `sanitize-public-docs --repo <path> [--write]`
- `validate`
```

- [ ] **Step 4: Create research lane reference**

Create `plugins/research-partner/references/review-lanes.md`:

```markdown
# Review Lanes

Use this reference when selecting or interpreting research-partner lanes.

## Default Command

Run `scripts/research_partner.py run --repo <repo> --output-dir <dir>` for end-to-end deterministic local review. Use `inventory` for preflight-only work. Use `bundle` when lane JSON files were produced elsewhere.

## Lanes

- `documentation-wizard`: documentation, methods prose, CLI/config instructions, and file-path promises
- `implementation-auditor`: code path, endpoint definitions, joins, recoding, and output generation
- `stats-reviewer`: estimand or prediction target, method fit, diagnostics, missingness, calibration, discrimination, and validation
- `scientific-reviewer`: claim type, bias, measurement validity, generalizability, and interpretation strength
- `literature-support-reviewer`: whether the actual method and study setting are supported directly or only by analogy
- `robustness-test-designer`: regression, fixture, invariance, perturbation, and smoke tests tied to concrete failure modes

Always separate descriptive, associational, causal, and predictive/prognostic claims. Always distinguish direct evidence, inference, and missing evidence.
```

- [ ] **Step 5: Create workspace policy reference**

Create `plugins/workspace-governor/references/workspace-policy.md`:

```markdown
# Workspace Policy

Use this reference for detailed workspace-governor behavior.

## Canonical Layout

- source code: `~/Projects/<slug>`
- runtime artifacts: `~/ProjectsRuntime/<slug>`
- research cloud homes: `~/Library/CloudStorage/OneDrive-Personal/Research/<slug>`
- side project cloud homes: `~/Library/CloudStorage/OneDrive-Personal/SideProjects/<slug>`

General software repos without strong managed-layout signals stay neutral rather than being forced into Research or SideProjects.

## Safe Flow

1. `assess --repo <path>`
2. review classification, doc contract, rewrite candidates, move plan, and publish preview
3. run `apply --audit <json>` only for approved moves
4. run `verify --manifest <json>` after apply

## Publish Flow

1. `publish-preview --repo <path>`
2. review public-doc rewrites and publish candidates
3. run `publish --repo <path> --approve-doc-review`

Publish copies runtime artifacts into dated cloud snapshots. It does not run normal analysis execution in cloud storage.
```

- [ ] **Step 6: Compact documentation-wizard skill**

Replace the body of `plugins/documentation-wizard/skills/documentation-wizard/SKILL.md` after frontmatter with:

```markdown
# Purpose

Use this skill when documentation must be checked against current code, CLI flags, config schemas, paths, or public/private documentation boundaries.

For detailed source-of-truth ordering and helper commands, read `references/documentation-policy.md`.

# Default Workflow

1. Run `scripts/documentation_wizard.py report --repo <path>` for evidence-backed drift review.
2. Use `interfaces` when the user asks specifically about CLI flags, config keys, or referenced paths.
3. Use `sanitize-public-docs --repo <path>` to preview public-doc path cleanup.
4. Use `sanitize-public-docs --repo <path> --write` only after the user approves edits.

# Output Expectations

Return concrete findings with source references, user impact, direct evidence versus inference, and the smallest correction that resolves the drift.
```

- [ ] **Step 7: Compact research-partner skills**

For `plugins/research-partner/skills/research-partner/SKILL.md`, keep frontmatter and replace the body with:

```markdown
# Purpose

Use this skill when a research analysis, manuscript claim, repository, or pipeline needs a data-first multi-lane review grounded in local artifacts.

Default to `scripts/research_partner.py run --repo <repo> --output-dir <dir>`. Read `references/review-lanes.md` before selecting or interpreting lanes.

# Workflow

1. Reconstruct local artifact and path truth before reviewing methods or claims.
2. Run only the lanes that match the user request.
3. Bundle lane outputs and preserve lane provenance.
4. Separate descriptive, associational, causal, and predictive/prognostic claims.
5. Separate direct evidence, inference, missing evidence, and implementation behavior.
```

For each lane-specific research skill, keep frontmatter and replace the body with this compact pattern, changing the first sentence to match the lane:

```markdown
# Purpose

Use this lane for the scope described in the frontmatter.

Read `references/review-lanes.md` for lane selection, evidence standards, and shared output expectations.

Return findings with lane name, severity, evidence basis, concrete implication, required checks, and recommended actions.
```

- [ ] **Step 8: Compact workspace-governor skill**

Replace the body of `plugins/workspace-governor/skills/workspace-governor/SKILL.md` after frontmatter with:

```markdown
# Purpose

Use this skill when workspace paths, canonical research layout, public/private docs, migration plans, or publish previews need audit or verification.

For canonical layout, safe-flow, and publish-flow details, read `references/workspace-policy.md`.

# Default Workflow

1. Prefer `scripts/workspace_governor.py assess --repo <path>` for a first non-mutating pass.
2. Surface classification, doc-contract, rewrite, move-plan, and publish-preview issues together.
3. Pause before mutating commands such as `apply` or `publish`.
4. Use `verify --manifest <json>` after any approved apply.

# Output Expectations

Report concrete path evidence, unresolved questions, publish risks, and verification steps. Do not merge destinations or silently rewrite files.
```

- [ ] **Step 9: Run compactness test**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_skills_are_compact_and_reference_detailed_policy_files -v
```

Expected: PASS.

- [ ] **Step 10: Run Plugin Eval token check**

Run:

```bash
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown > /tmp/documentation-wizard-token-pass.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown > /tmp/research-partner-token-pass.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown > /tmp/workspace-governor-token-pass.md
rg -n "Score:|token.*budget|description-trigger-weak" /tmp/documentation-wizard-token-pass.md /tmp/research-partner-token-pass.md /tmp/workspace-governor-token-pass.md
```

Expected: scores are not lower than the pre-plan scores unless the only new warning is an intentional reference-file tradeoff. No `description-trigger-weak` warning should appear.

- [ ] **Step 11: Run full tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: PASS.

- [ ] **Step 12: Commit**

Run:

```bash
git add plugins/*/skills plugins/*/references tests/test_plugins_and_agents.py
git commit -m "docs: move detailed skill policy into references"
```

---

### Task 7: Add Coverage Artifact Generation

**Files:**
- Create: `.coveragerc`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-06-11-plugin-efficiency-quality-followup-results.md`

- [ ] **Step 1: Create coverage config**

Create `.coveragerc`:

```ini
[run]
branch = True
source =
    plugins/documentation-wizard/scripts
    plugins/research-partner/scripts
    plugins/workspace-governor/scripts
    scripts

[report]
show_missing = True
skip_empty = True
omit =
    */__pycache__/*
    */tests/*
```

- [ ] **Step 2: Add README coverage command**

In `README.md`, after the plugin validators block, add:

````markdown
Generate coverage artifacts for Plugin Eval:

```bash
python -m coverage run -m unittest discover
python -m coverage xml
```
````

- [ ] **Step 3: Run coverage command**

Run:

```bash
python -m coverage run -m unittest discover
python -m coverage xml
```

Expected:

```text
Wrote XML report to coverage.xml
```

If `coverage` is not installed, run:

```bash
python -m pip install coverage
python -m coverage run -m unittest discover
python -m coverage xml
```

Then continue.

- [ ] **Step 4: Run Plugin Eval with coverage artifact present**

Run:

```bash
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown > /tmp/documentation-wizard-coverage-pass.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown > /tmp/research-partner-coverage-pass.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown > /tmp/workspace-governor-coverage-pass.md
rg -n "coverage-artifacts-unavailable|Score:" /tmp/documentation-wizard-coverage-pass.md /tmp/research-partner-coverage-pass.md /tmp/workspace-governor-coverage-pass.md
```

Expected: `Score:` lines appear. If `coverage-artifacts-unavailable` still appears, record that Plugin Eval does not pick up repo-root `coverage.xml` for per-plugin targets and do not invent a workaround.

- [ ] **Step 5: Commit**

Run:

```bash
git add .coveragerc README.md
git commit -m "test: add coverage artifact generation"
```

---

### Task 8: Final Validation, Deployment, And Results Note

**Files:**
- Create: `docs/superpowers/plans/2026-06-11-plugin-efficiency-quality-followup-results.md`

- [ ] **Step 1: Run full acceptance gates**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-quality-followup-smoke
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown > /tmp/documentation-wizard-quality-followup.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown > /tmp/research-partner-quality-followup.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown > /tmp/workspace-governor-quality-followup.md
```

Expected: all commands exit 0.

- [ ] **Step 2: Check for target Plugin Eval regressions**

Run:

```bash
if rg -n "interface-missing-websiteURL|interface-missing-privacyPolicyURL|interface-missing-termsOfServiceURL|description-trigger-weak" /tmp/documentation-wizard-quality-followup.md /tmp/research-partner-quality-followup.md /tmp/workspace-governor-quality-followup.md; then
  exit 1
fi
rg -n "Score:|py-complexity-high|py-long-lines|token.*budget|coverage-artifacts-unavailable" /tmp/documentation-wizard-quality-followup.md /tmp/research-partner-quality-followup.md /tmp/workspace-governor-quality-followup.md
```

Expected: no interface or trigger regressions. Complexity, long-line, token, and coverage lines should be recorded in the results note with before/after status.

- [ ] **Step 3: Deploy installed copies**

Run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
python ~/.codex/plugins/documentation-wizard/scripts/documentation_wizard.py validate
python ~/.codex/plugins/research-partner/scripts/research_partner.py validate
python ~/.codex/plugins/workspace-governor/scripts/workspace_governor.py validate
python ~/.codex/plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-quality-followup-installed-smoke
```

Expected: deploy returns `"status": "ok"` and all installed validators return `"passed": true`.

- [ ] **Step 4: Create results note**

Create `docs/superpowers/plans/2026-06-11-plugin-efficiency-quality-followup-results.md`:

```markdown
# Plugin Efficiency And Quality Follow-Up Results

## Commands Run

- `python -m unittest tests/test_plugins_and_agents.py`
- `python -m unittest discover -s plugins/documentation-wizard/tests -v`
- `python -m unittest discover -s plugins/research-partner/tests -v`
- `python -m unittest discover -s plugins/workspace-governor/tests -v`
- `python plugins/documentation-wizard/scripts/documentation_wizard.py validate`
- `python plugins/research-partner/scripts/research_partner.py validate`
- `python plugins/workspace-governor/scripts/workspace_governor.py validate`
- `python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-quality-followup-smoke`
- `python scripts/deploy_plugins.py install --source-root . --home ~`
- `python ~/.codex/plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-quality-followup-installed-smoke`
- Plugin Eval for documentation-wizard, research-partner, and workspace-governor

## Results

- Root regression suite:
- Plugin-local suites:
- Source validators:
- Installed validators:
- Research Partner source smoke:
- Research Partner installed smoke:
- Documentation Wizard Plugin Eval:
- Research Partner Plugin Eval:
- Workspace Governor Plugin Eval:
- Coverage artifact:

## Remaining Work

- Remaining complexity warnings:
- Remaining token warnings:
- Remaining long-line warnings:
- Remaining coverage limitations:
```

Replace every blank value with actual command results before committing. Do not leave empty bullets.

- [ ] **Step 5: Commit results**

Run:

```bash
git add docs/superpowers/plans/2026-06-11-plugin-efficiency-quality-followup-results.md
git commit -m "docs: record plugin efficiency follow-up results"
```

---

## Acceptance Gates

The follow-up is complete only when these pass:

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-quality-followup-smoke
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown
python scripts/deploy_plugins.py install --source-root . --home ~
python ~/.codex/plugins/documentation-wizard/scripts/documentation_wizard.py validate
python ~/.codex/plugins/research-partner/scripts/research_partner.py validate
python ~/.codex/plugins/workspace-governor/scripts/workspace_governor.py validate
```

Manual checks:

- plugin-level READMEs state the current source repo and deploy-target model.
- `research_partner.py run --lane stats-reviewer` writes only the requested lane plus preflight and bundle.
- bundled lane findings keep lane provenance and evidence basis.
- Plugin Eval has no missing interface URL findings and no weak trigger description findings.
- Results note records remaining warnings honestly rather than claiming they disappeared.

## Self-Review

Spec coverage:

- README drift: Task 1.
- Better behavioral reliability: Task 2.
- Large script decomposition: Tasks 3, 4, and 5.
- Token-cost reduction: Task 6.
- Coverage artifacts: Task 7.
- Full validation and deployment: Task 8.

Placeholder scan:

- No `TBD`, `TODO`, or unspecified implementation placeholders are present.
- Refactor tasks name exact files, exact functions to move, exact wrapper signatures, and exact verification commands.

Type consistency:

- Existing public CLI script filenames stay unchanged.
- `run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None)` remains the public research-partner signature.
- Extracted modules use dependency injection for peer plugin scripts so they do not create duplicate discovery logic.
- Golden tests use the existing `unittest` style and existing module loaders.
