# Plugin Eval Warnings Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the remaining Plugin Eval warnings from the efficiency follow-up (`py-complexity-high`, `py-long-lines`, `coverage-artifacts-unavailable`, `trigger_cost_tokens-budget-high`) and materially reduce `deferred_cost_tokens-budget-high` without changing public CLI contracts.

**Architecture:** Plugin Eval uses static heuristics, not real cyclomatic complexity. Python “complexity” is `1 + count(if|elif|for|while|except|and|or)` per file, with the max across all plugin Python files compared to threshold `18`. Long-line warnings clear only when **zero** lines exceed 120 characters. Coverage scoring looks for `coverage.xml` **inside each plugin directory**. Research-partner trigger cost is dominated by nine implicit skill descriptions; lane skills move to `allow_implicit_invocation: false` via `agents/openai.yaml`. Deferred token cost counts nearly all plugin text (scripts, README, references, tests, assets); meaningful reduction requires smaller/shorter deferred files, not just moving code between Python modules.

**Tech Stack:** Python 3 standard library, `unittest`, `coverage`, JSON Plugin Eval output, `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js`.

**Branch:** Continue from `plugin-efficiency-quality-followup` (worktree at `~/.config/superpowers/worktrees/codex-personal-plugins/plugin-efficiency-quality-followup`).

---

## Scope

### In scope

- add Plugin Eval regression harness with frozen baseline metrics
- generate per-plugin `coverage.xml` artifacts Plugin Eval can discover
- eliminate all Python lines >120 characters under `plugins/*/scripts/`
- split Python files until Plugin Eval file-level complexity score is `<18` everywhere
- mark research-partner lane skills explicit-only to clear trigger budget warning
- trim deferred surface area where safe (README, relocate plugin-local tests to repo `tests/plugins/`)
- rerun validators, deploy, and record results

### Out of scope

- changing plugin names, manifest paths, or CLI entrypoint filenames
- merging or deleting research-partner lane skills (validators require all eight skill files)
- expecting `deferred_cost_tokens` to reach corpus “moderate” band (≤900 tokens) without removing most Python from plugin directories — document honest residual if still heavy

### Current baseline (2026-06-12)

| Plugin | Score | py complexity max | long lines | trigger | deferred |
|--------|-------|-------------------|------------|---------|----------|
| documentation-wizard | 86 | 81 | 13 | 109 (moderate) | 11843 (heavy) |
| research-partner | 82 | 72 | 38 | 356 (heavy) | 12682 (heavy) |
| workspace-governor | 86 | 253 | 30 | 104 (moderate) | 23779 (heavy) |

All three: `coverage-artifacts-unavailable` (INFO, −0.25).

Worst complexity files:

- `plugins/workspace-governor/scripts/workspace_governor.py` — 253
- `plugins/documentation-wizard/scripts/dw_core/interfaces.py` — 81
- `plugins/research-partner/scripts/research_partner.py` — 72

## File Structure

Create:

- `scripts/plugin_eval_regression.py` — mirrors Plugin Eval Python heuristics for fast local gates
- `scripts/generate_plugin_coverage.py` — writes per-plugin `coverage.xml`
- `tests/plugin_eval_baseline.json` — frozen pre-remediation metrics
- `plugins/research-partner/skills/*/agents/openai.yaml` — eight lane skills (not `research-partner`)
- `plugins/workspace-governor/scripts/wg_core/paths.py`
- `plugins/workspace-governor/scripts/wg_core/docs_bridge.py`
- `plugins/workspace-governor/scripts/wg_core/git_io.py`
- `plugins/workspace-governor/scripts/wg_core/destination.py`
- `plugins/workspace-governor/scripts/wg_core/commands_audit.py`
- `plugins/workspace-governor/scripts/wg_core/commands_assess.py`
- `plugins/workspace-governor/scripts/wg_core/commands_publish.py`
- `plugins/workspace-governor/scripts/wg_core/metadata_parse.py`
- `plugins/workspace-governor/scripts/wg_core/metadata_profile.py`
- `plugins/documentation-wizard/scripts/dw_core/cli_flags.py`
- `plugins/documentation-wizard/scripts/dw_core/schema_paths.py`
- `plugins/research-partner/scripts/rp_core/lane_runners.py`
- `plugins/research-partner/scripts/rp_core/review_flow.py`
- `tests/plugins/documentation-wizard/test_documentation_wizard.py` (moved)
- `tests/plugins/research-partner/test_research_partner.py` (moved)
- `tests/plugins/workspace-governor/test_workspace_governor.py` (moved)
- `docs/superpowers/plans/2026-06-12-plugin-eval-warnings-remediation-results.md`

Modify:

- `tests/test_plugins_and_agents.py`
- `README.md`
- `.gitignore`
- `.coveragerc`
- `plugins/*/scripts/**/*.py` (long-line wraps + complexity splits)
- `plugins/research-partner/skills/*/agents/openai.yaml` (lane skills only)

Delete after move:

- `plugins/documentation-wizard/tests/test_documentation_wizard.py`
- `plugins/research-partner/tests/test_research_partner.py`
- `plugins/workspace-governor/tests/test_workspace_governor.py`

---

### Task 1: Add Plugin Eval Regression Harness And Baseline

**Files:**
- Create: `scripts/plugin_eval_regression.py`
- Create: `tests/plugin_eval_baseline.json`
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add failing regression helper test**

Add to `tests/test_plugins_and_agents.py`:

```python
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
        for plugin_name, expected in baseline["plugins"].items():
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
            if "max_complexity" in expected:
                self.assertLessEqual(
                    metrics["max_complexity"],
                    expected["max_complexity"],
                    f"{plugin_name} regressed on complexity",
                )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests -v
```

Expected: FAIL (`plugin_eval_regression` missing and/or complexity ≥18).

- [ ] **Step 3: Create heuristic mirror**

Create `scripts/plugin_eval_regression.py`:

```python
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

DECISION_PATTERNS = [
    re.compile(r"\bif\b"),
    re.compile(r"\belif\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\bexcept\b"),
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
]


def plugin_eval_complexity(source: str) -> int:
    return 1 + sum(len(pattern.findall(source)) for pattern in DECISION_PATTERNS)


def analyze_plugin_python(scripts_root: Path) -> dict[str, Any]:
    max_complexity = 0
    long_lines = 0
    per_file: list[dict[str, Any]] = []
    for path in sorted(scripts_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        complexity = plugin_eval_complexity(text)
        file_long_lines = sum(1 for line in text.splitlines() if len(line) > 120)
        max_complexity = max(max_complexity, complexity)
        long_lines += file_long_lines
        per_file.append(
            {
                "path": str(path),
                "complexity": complexity,
                "long_lines": file_long_lines,
            }
        )
    return {
        "max_complexity": max_complexity,
        "long_lines": long_lines,
        "files": per_file,
    }


def run_plugin_eval_json(plugin_root: Path, plugin_eval_js: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["node", str(plugin_eval_js), "analyze", str(plugin_root), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def check_ids(payload: dict[str, Any]) -> set[str]:
    return {check["id"] for check in payload.get("checks", []) if check.get("status") in {"warn", "fail"}}
```

- [ ] **Step 4: Capture baseline JSON**

Run:

```bash
python3 <<'PY'
import json
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from plugin_eval_regression import analyze_plugin_python, run_plugin_eval_json

ROOT = Path(".")
PLUGIN_EVAL = Path("/Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js")
plugins = {}
for name in ["documentation-wizard", "research-partner", "workspace-governor"]:
    scripts = analyze_plugin_python(ROOT / "plugins" / name / "scripts")
    payload = run_plugin_eval_json(ROOT / "plugins" / name, PLUGIN_EVAL)
    plugins[name] = {
        "score": payload.get("score", {}).get("value"),
        "max_complexity": scripts["max_complexity"],
        "long_lines": scripts["long_lines"],
        "trigger_cost_tokens": payload.get("budgets", {}).get("trigger_cost_tokens", {}).get("value"),
        "deferred_cost_tokens": payload.get("budgets", {}).get("deferred_cost_tokens", {}).get("value"),
        "warn_check_ids": sorted(check["id"] for check in payload.get("checks", []) if check.get("status") == "warn"),
    }
(ROOT / "tests" / "plugin_eval_baseline.json").write_text(json.dumps({"plugins": plugins}, indent=2) + "\n", encoding="utf-8")
print(json.dumps(plugins, indent=2))
PY
```

Expected: writes `tests/plugin_eval_baseline.json` with current metrics.

- [ ] **Step 5: Temporarily relax complexity assertion for baseline capture**

Until later tasks land, change `test_plugin_python_heuristics_match_baseline_or_improve` to only assert baseline file exists and `long_lines` baseline recorded. Re-tighten in Task 8.

- [ ] **Step 6: Commit**

```bash
git add scripts/plugin_eval_regression.py tests/plugin_eval_baseline.json tests/test_plugins_and_agents.py
git commit -m "test: add plugin eval regression harness and baseline"
```

---

### Task 2: Generate Per-Plugin Coverage Artifacts

**Files:**
- Create: `scripts/generate_plugin_coverage.py`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add failing coverage artifact test**

Add to `PluginEvalRegressionTests`:

```python
    def test_plugins_have_local_coverage_artifacts(self) -> None:
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            coverage_path = PLUGINS_ROOT / plugin_name / "coverage.xml"
            self.assertTrue(coverage_path.exists(), f"missing {coverage_path}")
            text = coverage_path.read_text(encoding="utf-8")
            self.assertIn("coverage", text)
            self.assertIn("line-rate", text)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_plugins_have_local_coverage_artifacts -v
```

Expected: FAIL — no per-plugin `coverage.xml`.

- [ ] **Step 3: Create generator script**

Create `scripts/generate_plugin_coverage.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PLUGINS = [
    "documentation-wizard",
    "research-partner",
    "workspace-governor",
]


def generate_for_plugin(repo_root: Path, plugin_name: str) -> Path:
    source = f"plugins/{plugin_name}/scripts"
    test_dir = f"plugins/{plugin_name}/tests"
    output = repo_root / "plugins" / plugin_name / "coverage.xml"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            f"--source={source}",
            "-m",
            "unittest",
            "discover",
            "-s",
            test_dir,
        ],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "coverage", "xml", "-o", str(output)],
        cwd=repo_root,
        check=True,
    )
    return output


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    for plugin_name in PLUGINS:
        path = generate_for_plugin(repo_root, plugin_name)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Ignore generated artifacts**

Add to `.gitignore`:

```gitignore
plugins/*/coverage.xml
```

- [ ] **Step 5: Document command in README**

After the existing coverage block, add:

````markdown
Generate per-plugin coverage artifacts for Plugin Eval:

```bash
python scripts/generate_plugin_coverage.py
```
````

- [ ] **Step 6: Run generator and test**

```bash
python scripts/generate_plugin_coverage.py
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_plugins_have_local_coverage_artifacts -v
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format json | python3 -c "import json,sys; d=json.load(sys.stdin); print([c['id'] for c in d['checks'] if 'coverage' in c['id']])"
```

Expected: test PASS; Plugin Eval no longer emits `coverage-artifacts-unavailable` when run from repo root with artifacts present.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_plugin_coverage.py .gitignore README.md tests/test_plugins_and_agents.py
git commit -m "test: generate per-plugin coverage artifacts"
```

---

### Task 3: Eliminate Python Long Lines

**Files:**
- Modify: all `plugins/*/scripts/**/*.py` with long lines (81 total today)
- Modify: `scripts/plugin_eval_regression.py`
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add failing long-line gate**

Add to `PluginEvalRegressionTests`:

```python
    def test_plugin_python_has_no_lines_over_120_chars(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            metrics = analyze_plugin_python(PLUGINS_ROOT / plugin_name / "scripts")
            self.assertEqual(metrics["long_lines"], 0, plugin_name)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_plugin_python_has_no_lines_over_120_chars -v
```

Expected: FAIL — 81 long lines.

- [ ] **Step 3: Wrap long lines mechanically**

For each file reported by:

```bash
python3 <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from plugin_eval_regression import analyze_plugin_python
root = Path("plugins")
for plugin in ["documentation-wizard", "research-partner", "workspace-governor"]:
    for item in analyze_plugin_python(root / plugin / "scripts")["files"]:
        if item["long_lines"]:
            print(item["path"], item["long_lines"])
PY
```

Apply wrapping rules:

- break long dict literals across lines
- parenthesize and break long `return` expressions
- split long f-strings into concatenated parts
- do **not** change behavior or string contents

Priority files (highest counts): `rp_core/lanes.py`, `workspace_governor.py`, `dw_core/reporting.py`, `dw_core/interfaces.py`.

- [ ] **Step 4: Re-run long-line test and Plugin Eval**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_plugin_python_has_no_lines_over_120_chars -v
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format json | python3 -c "import json,sys; d=json.load(sys.stdin); print('py-long-lines' in {c['id'] for c in d['checks']})"
```

Expected: test PASS; `py-long-lines` absent from all three plugins.

- [ ] **Step 5: Run full suites**

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/*/scripts
git commit -m "style: wrap plugin python lines for plugin eval"
```

---

### Task 4: Clear Research-Partner Trigger Budget Warning

**Files:**
- Create: `plugins/research-partner/skills/assess-literature-support/agents/openai.yaml` (and seven sibling lane skills)
- Modify: `tests/test_plugins_and_agents.py`

Lane skills receiving explicit-only policy (all except `research-partner`):

- `assess-literature-support`
- `design-robustness-tests`
- `inspect-analysis-artifacts`
- `review-documentation-consistency`
- `review-implementation-validity`
- `review-scientific-interpretation`
- `review-statistical-validity`
- `synthesize-review`

- [ ] **Step 1: Add failing trigger budget test**

```python
    def test_research_partner_trigger_budget_is_not_heavy(self) -> None:
        if not PLUGIN_EVAL_JS.exists():
            self.skipTest("plugin-eval not installed")
        from scripts.plugin_eval_regression import run_plugin_eval_json

        payload = run_plugin_eval_json(PLUGINS_ROOT / "research-partner", PLUGIN_EVAL_JS)
        band = payload["budgets"]["trigger_cost_tokens"]["band"]
        self.assertIn(band, {"good", "moderate"}, f"trigger band is {band}")
        warn_ids = {check["id"] for check in payload["checks"] if check.get("status") == "warn"}
        self.assertNotIn("trigger_cost_tokens-budget-high", warn_ids)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_research_partner_trigger_budget_is_not_heavy -v
```

Expected: FAIL — trigger band `heavy` (356 tokens).

- [ ] **Step 3: Add explicit-only policy files**

For each lane skill directory listed above, create `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Do **not** add this file to `skills/research-partner/` — it must remain implicitly invocable.

- [ ] **Step 4: Re-run trigger test and validate**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_research_partner_trigger_budget_is_not_heavy -v
python plugins/research-partner/scripts/research_partner.py validate
```

Expected: trigger band `good` or `moderate` (~106 tokens); validate still `passed: true`.

- [ ] **Step 5: Commit**

```bash
git add plugins/research-partner/skills tests/test_plugins_and_agents.py
git commit -m "docs: mark research lane skills explicit-only for eval budget"
```

---

### Task 5: Split Workspace Governor Entry Module For Complexity

**Files:**
- Create: `plugins/workspace-governor/scripts/wg_core/paths.py`
- Create: `plugins/workspace-governor/scripts/wg_core/docs_bridge.py`
- Create: `plugins/workspace-governor/scripts/wg_core/git_io.py`
- Create: `plugins/workspace-governor/scripts/wg_core/destination.py`
- Create: `plugins/workspace-governor/scripts/wg_core/commands_audit.py`
- Create: `plugins/workspace-governor/scripts/wg_core/commands_assess.py`
- Create: `plugins/workspace-governor/scripts/wg_core/commands_publish.py`
- Modify: `plugins/workspace-governor/scripts/workspace_governor.py`

- [ ] **Step 1: Add failing workspace-governor complexity test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_workspace_governor_plugin_eval_complexity_under_threshold -v
```

Expected: FAIL — `workspace_governor.py` scores 253.

- [ ] **Step 3: Extract path and IO helpers**

Move unchanged into new modules:

**`wg_core/paths.py`:** `canonical_project_name`, `now_stamp`, `metadata_list`, `normalized_project_slug`, `default_cloud_home`, `configured_cloud_home`, `configured_runtime_home`, `configured_publish_root_name`, `configured_publish_layout`, `project_publish_denylist`, `iter_repo_files`, `public_doc_paths`

**`wg_core/git_io.py`:** `write_json`, `read_json`, `run_git`, `git_status`, `tree_signature`, `signatures_match`, `cleanup_path`

**`wg_core/docs_bridge.py`:** `ensure_dual_doc_contract`, `parse_doc_ref_path`, `load_doc_ref_line`, `referenced_path_token`, `filter_doc_findings`, `filter_sanitize_preview`, `run_doc_wizard`, `doc_policy_report`

**`wg_core/destination.py`:** `immediate_root_label`, `child_dirs`, `suggested_destination`, `rewrite_candidates`, `build_dry_run_questions`

Use `_host.wg()` for callbacks already established in `wg_core`.

- [ ] **Step 4: Extract command bodies**

**`wg_core/commands_audit.py`:** `audit`, `dry_run`

**`wg_core/commands_assess.py`:** `assess`

**`wg_core/commands_publish.py`:** `verify_git_copy`, `collect_publish_destination_checks`, `publish_preview`, `publish`, `publish_snapshot_dir`

Keep in `workspace_governor.py` only: imports, `_peer_plugin_root`, `validate_plugin`, `parse_classifications`, `parse_repo_kind`, `build_parser`, `command_payload`, `main`, and thin re-exports tests import from `WORKSPACE_GOVERNOR.*`.

- [ ] **Step 5: Run workspace-governor gates**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_workspace_governor_plugin_eval_complexity_under_threshold -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_general_repo_assessment_has_no_move_plan -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_publish_candidate_split_layout_maps_manifest_with_year -v
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/workspace-governor/scripts/workspace_governor.py assess --repo tests/fixtures/research_repo --roots tests/fixtures --snapshot-id complexity-smoke
```

Expected: complexity test PASS; all others PASS; `assess` returns `"status": "ok"`.

- [ ] **Step 6: Commit**

```bash
git add plugins/workspace-governor/scripts
git commit -m "refactor: split workspace governor entry module for eval complexity"
```

---

### Task 6: Split Workspace Governor Metadata Module

**Files:**
- Create: `plugins/workspace-governor/scripts/wg_core/metadata_parse.py`
- Create: `plugins/workspace-governor/scripts/wg_core/metadata_profile.py`
- Modify: `plugins/workspace-governor/scripts/wg_core/metadata.py`

- [ ] **Step 1: Run complexity test to confirm metadata file still fails**

```bash
python3 <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
from plugin_eval_regression import plugin_eval_complexity
text = Path('plugins/workspace-governor/scripts/wg_core/metadata.py').read_text()
print(plugin_eval_complexity(text))
PY
```

Expected: `80` (still ≥18).

- [ ] **Step 2: Split metadata**

Move into `metadata_parse.py`: `load_text`, `slugify`, `extract_scalar`, `extract_list`, `parse_metadata_text`, regex constants used only there.

Move into `metadata_profile.py`: `read_metadata_texts`, `repo_software_signals`, `infer_project_profile`, `review_analysis_registry`.

Replace `metadata.py` with re-exports:

```python
from .metadata_parse import load_text, parse_metadata_text
from .metadata_profile import infer_project_profile
```

- [ ] **Step 3: Re-run workspace-governor complexity test**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_workspace_governor_plugin_eval_complexity_under_threshold -v
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_workspace_governor_accepts_general_project_type_metadata -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/workspace-governor/scripts/wg_core
git commit -m "refactor: split workspace governor metadata helpers"
```

---

### Task 7: Split Documentation Wizard And Research Partner Complexity Files

**Files:**
- Create: `plugins/documentation-wizard/scripts/dw_core/cli_flags.py`
- Create: `plugins/documentation-wizard/scripts/dw_core/schema_paths.py`
- Modify: `plugins/documentation-wizard/scripts/dw_core/interfaces.py`
- Create: `plugins/research-partner/scripts/rp_core/lane_runners.py`
- Create: `plugins/research-partner/scripts/rp_core/review_flow.py`
- Modify: `plugins/research-partner/scripts/rp_core/lanes.py`
- Modify: `plugins/research-partner/scripts/research_partner.py`

- [ ] **Step 1: Add per-plugin complexity tests**

```python
    def test_documentation_wizard_plugin_eval_complexity_under_threshold(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        metrics = analyze_plugin_python(PLUGINS_ROOT / "documentation-wizard" / "scripts")
        self.assertLess(metrics["max_complexity"], 18)

    def test_research_partner_plugin_eval_complexity_under_threshold(self) -> None:
        from scripts.plugin_eval_regression import analyze_plugin_python

        metrics = analyze_plugin_python(PLUGINS_ROOT / "research-partner" / "scripts")
        self.assertLess(metrics["max_complexity"], 18)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_documentation_wizard_plugin_eval_complexity_under_threshold -v
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_research_partner_plugin_eval_complexity_under_threshold -v
```

Expected: FAIL — DW `interfaces.py` 81, RP `research_partner.py` 72.

- [ ] **Step 3: Split documentation-wizard interfaces**

Move from `dw_core/interfaces.py` into:

- `cli_flags.py`: `ARGPARSE_CALL_RE`, `CLICK_OPTION_CALL_RE`, `TYPER_OPTION_IMPORT_RE`, `FLAG_RE`, `extract_cli_flags`, `public_cli_surface_paths`
- `schema_paths.py`: `walk_schema`, `extract_interfaces`, `MARKDOWN_LINK_RE`, `PATH_TOKEN_RE`, `PATH_CONTINUATION_CHARS`, `DOC_SUFFIXES`

Leave `interfaces.py` as compatibility re-exports only.

- [ ] **Step 4: Split research-partner lanes and entry script**

Move from `rp_core/lanes.py` into `lane_runners.py`: individual lane functions (`implementation_auditor_lane`, `stats_reviewer_lane`, etc.).

Move into `review_flow.py`: `execute_lane`, `run_review`.

Move validation-only helpers out of `research_partner.py` into `rp_core/workspace.py` or new `rp_core/validate_bundle.py` until `research_partner.py` scores `<18`.

- [ ] **Step 5: Run plugin gates**

```bash
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_documentation_wizard_plugin_eval_complexity_under_threshold -v
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_research_partner_plugin_eval_complexity_under_threshold -v
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/rp-complexity-smoke
```

Expected: all PASS; smoke `status: ok`.

- [ ] **Step 6: Commit**

```bash
git add plugins/documentation-wizard/scripts plugins/research-partner/scripts tests/test_plugins_and_agents.py
git commit -m "refactor: split plugin scripts for eval complexity thresholds"
```

---

### Task 8: Reduce Deferred Token Surface Area

**Files:**
- Create: `tests/plugins/documentation-wizard/test_documentation_wizard.py`
- Create: `tests/plugins/research-partner/test_research_partner.py`
- Create: `tests/plugins/workspace-governor/test_workspace_governor.py`
- Delete: `plugins/*/tests/test_*.py`
- Modify: `README.md`, `.coveragerc`, `scripts/generate_plugin_coverage.py`, `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add deferred improvement test**

```python
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
                int(previous * 0.85),
                f"{plugin_name} deferred tokens {current} did not improve 15% from {previous}",
            )
```

- [ ] **Step 2: Move plugin-local tests to repo tests tree**

Move files unchanged:

- `plugins/documentation-wizard/tests/test_documentation_wizard.py` → `tests/plugins/documentation-wizard/test_documentation_wizard.py`
- `plugins/research-partner/tests/test_research_partner.py` → `tests/plugins/research-partner/test_research_partner.py`
- `plugins/workspace-governor/tests/test_workspace_governor.py` → `tests/plugins/workspace-governor/test_workspace_governor.py`

Update module loaders in moved tests:

```python
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
```

instead of `parents[2]`.

- [ ] **Step 3: Update coverage generator and README**

Change `scripts/generate_plugin_coverage.py` test discovery to:

```python
test_dir = f"tests/plugins/{plugin_name}"
```

Update README test commands to include:

```bash
python -m unittest discover -s tests/plugins/documentation-wizard -v
python -m unittest discover -s tests/plugins/research-partner -v
python -m unittest discover -s tests/plugins/workspace-governor -v
```

- [ ] **Step 4: Trim plugin README files**

Reduce each plugin `README.md` to ≤40 lines by moving extended examples into existing `references/*.md` files. Keep required source-of-truth fragments from Task 1 of the prior plan.

- [ ] **Step 5: Run deferred test and full suites**

```bash
python scripts/generate_plugin_coverage.py
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s tests/plugins/documentation-wizard -v
python -m unittest discover -s tests/plugins/research-partner -v
python -m unittest discover -s tests/plugins/workspace-governor -v
python -m unittest tests.test_plugins_and_agents.PluginEvalRegressionTests.test_deferred_token_budget_improved_from_baseline -v
```

Expected: deferred tokens drop ≥15% per plugin. If still above corpus “heavy” band, record honestly in results — that is acceptable if improvement test passes.

- [ ] **Step 6: Commit**

```bash
git add tests/plugins plugins README.md .coveragerc scripts/generate_plugin_coverage.py
git add -u plugins/*/tests
git commit -m "chore: reduce deferred eval surface by relocating plugin tests"
```

---

### Task 9: Final Validation And Results

**Files:**
- Create: `docs/superpowers/plans/2026-06-12-plugin-eval-warnings-remediation-results.md`
- Modify: `tests/test_plugins_and_agents.py` (re-enable strict complexity assertions)
- Modify: `tests/plugin_eval_baseline.json` (refresh post-remediation snapshot)

- [ ] **Step 1: Tighten regression tests**

Ensure `PluginEvalRegressionTests` asserts for all three plugins:

- `max_complexity < 18`
- `long_lines == 0`
- no warn checks: `py-complexity-high`, `py-long-lines`, `coverage-artifacts-unavailable`
- research-partner: no `trigger_cost_tokens-budget-high`

- [ ] **Step 2: Run full acceptance gates**

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s tests/plugins/documentation-wizard -v
python -m unittest discover -s tests/plugins/research-partner -v
python -m unittest discover -s tests/plugins/workspace-governor -v
python scripts/generate_plugin_coverage.py
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/rp-eval-remediation-smoke
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown > /tmp/dw-eval-remediation.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown > /tmp/rp-eval-remediation.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown > /tmp/wg-eval-remediation.md
if rg -n "interface-missing-websiteURL|interface-missing-privacyPolicyURL|interface-missing-termsOfServiceURL|description-trigger-weak" /tmp/dw-eval-remediation.md /tmp/rp-eval-remediation.md /tmp/wg-eval-remediation.md; then exit 1; fi
rg -n "Score:|py-complexity-high|py-long-lines|trigger_cost_tokens-budget-high|coverage-artifacts-unavailable|deferred_cost_tokens-budget-high" /tmp/dw-eval-remediation.md /tmp/rp-eval-remediation.md /tmp/wg-eval-remediation.md
python scripts/deploy_plugins.py install --source-root . --home ~
```

Expected: no interface/trigger regressions; `py-complexity-high`, `py-long-lines`, `coverage-artifacts-unavailable`, `trigger_cost_tokens-budget-high` cleared; `deferred_cost_tokens-budget-high` improved or documented.

- [ ] **Step 3: Write results note**

Create `docs/superpowers/plans/2026-06-12-plugin-eval-warnings-remediation-results.md` with filled bullets for every command, before/after scores, and honest residual deferred-token status.

- [ ] **Step 4: Refresh baseline JSON to post-remediation values**

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-plugin-eval-warnings-remediation-results.md tests/plugin_eval_baseline.json tests/test_plugins_and_agents.py
git commit -m "docs: record plugin eval warnings remediation results"
```

---

## Acceptance Gates

Required clears:

```bash
python -m unittest tests/test_plugins_and_agents.py
python scripts/generate_plugin_coverage.py
# Plugin Eval per plugin must NOT warn on:
# py-complexity-high, py-long-lines, coverage-artifacts-unavailable
# research-partner must NOT warn on trigger_cost_tokens-budget-high
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format json
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format json
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format json
```

Deferred tokens:

- required: ≥15% reduction per plugin vs `tests/plugin_eval_baseline.json`
- optional stretch: `deferred_cost_tokens` band improves from `heavy` to `moderate` (unlikely without major code removal)

Manual checks:

- all three CLI entrypoints unchanged
- research-partner `validate` still passes with eight lane skills present
- lane skills are explicit-only; `research-partner` skill remains implicit
- per-plugin `coverage.xml` generated locally (gitignored), Plugin Eval sees it during analyze

## Self-Review

**Spec coverage:**

- complexity: Tasks 5–7
- long lines: Task 3
- coverage artifacts: Task 2
- trigger budget: Task 4
- deferred tokens: Task 8 (partial, honest)
- validation: Task 9

**Placeholder scan:** no TBD/TODO steps; commands and code blocks are concrete.

**Type consistency:** `analyze_plugin_python`, `run_plugin_eval_json`, and `PluginEvalRegressionTests` names used consistently across tasks.
