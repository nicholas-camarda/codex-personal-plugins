# Plugin Quality Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `documentation-wizard`, `research-partner`, and `workspace-governor` up to reliable local-plugin quality, including real `research-partner` lane execution rather than only preflight and bundling.

**Architecture:** Move authored plugin source into a dedicated git-backed Codex plugin source repo that uses the documented repo marketplace layout: `$REPO_ROOT/.agents/plugins/marketplace.json` plus plugins under `$REPO_ROOT/plugins/`. Keep `~/.codex/plugins` as the personal install/cache location, not the source of truth. Add a first-class `research-partner run` command that produces preflight, lane outputs, and a final bundle from actual local functions and sibling plugin CLIs. Fix plugin metadata and skill trigger text without adding compatibility hacks or temporary rescue paths.

**Tech Stack:** Python 3 standard library, `unittest`, JSON CLI payloads, local Codex plugin manifests, Plugin Eval CLI via `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js`.

---

## Scope

This plan covers one integrated plugin-quality pass because the three plugins are intentionally coupled:

- `documentation-wizard` provides the documentation-consistency lane.
- `workspace-governor` provides workspace topology and publish-safety evidence.
- `research-partner` orchestrates research review lanes and must execute those lanes directly.

Do not split the work into unrelated rewrites. Keep changes small, tested, and directly tied to evaluator findings or the missing lane execution behavior.

## OpenAI/Codex Layout Decision

Use the documented Codex repo marketplace layout for development:

- Source repo: `/Users/ncamarda/Projects/codex-personal-plugins`
- Git remote: `https://github.com/nicholas-camarda/codex-personal-plugins.git`
- Repo marketplace: `/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json`
- Authored plugins: `/Users/ncamarda/Projects/codex-personal-plugins/plugins/<plugin-name>/`
- Personal installed plugins: `/Users/ncamarda/.codex/plugins/<plugin-name>/`

Rationale:

- OpenAI's Build plugins docs describe repo marketplaces with plugins stored under `$REPO_ROOT/plugins/` and marketplace metadata under `$REPO_ROOT/.agents/plugins/marketplace.json`: https://developers.openai.com/codex/plugins/build
- OpenAI's AGENTS.md and configuration docs describe Codex project-root discovery as starting at the project root, typically the Git root: https://developers.openai.com/codex/guides/agents-md and https://developers.openai.com/codex/config-advanced
- OpenAI's skills/plugin docs distinguish skills as the authoring format and plugins as the installable distribution unit: https://developers.openai.com/codex/skills

Resolved decisions:

- Use `/Users/ncamarda/Projects/codex-personal-plugins` as the canonical local source repo.
- Use `https://github.com/nicholas-camarda/codex-personal-plugins.git` as the canonical remote URL.
- Use repo-specific manifest URLs that point to `https://github.com/nicholas-camarda/codex-personal-plugins`.
- Implement deterministic local `research-partner` lane execution first. Do not add subagent-backed lane orchestration in this pass.
- Treat installed personal plugin copies under `/Users/ncamarda/.codex/plugins/<plugin-name>` as generated deploy targets once the source repo is established. The deploy script may overwrite `/Users/ncamarda/.codex/plugins/documentation-wizard`, `/Users/ncamarda/.codex/plugins/research-partner`, and `/Users/ncamarda/.codex/plugins/workspace-governor` from the git-backed source repo.

After Task 0, all plan paths are relative to `/Users/ncamarda/Projects/codex-personal-plugins` unless an absolute path is shown.

## File Structure

Create:

- `/Users/ncamarda/Projects/codex-personal-plugins/`
  - Git-backed source repo and Codex project root.

- `.agents/plugins/marketplace.json`
  - Repo marketplace listing the three local plugins by `./plugins/<name>` path.

Modify:

- `AGENTS.md`
  - Repo-local instructions for plugin development, testing, deployment, and OpenAI/Codex layout rules.

- `scripts/deploy_plugins.py`
  - Change from "source root must equal home plugin workspace" to "copy selected repo plugins into the personal install root, then validate installed copies".

- `plugins/<plugin-name>/.codex-plugin/plugin.json` in each plugin root:
  - Add `interface.websiteURL`, `interface.privacyPolicyURL`, and `interface.termsOfServiceURL`.
  - Keep all URLs real. Use the existing GitHub identity; do not use `example.com`.

- `plugins/documentation-wizard/skills/documentation-wizard/SKILL.md`
  - Rewrite frontmatter description to start with a clear `Use when...` trigger.

- `plugins/workspace-governor/skills/workspace-governor/SKILL.md`
  - Rewrite frontmatter description to start with a clear `Use when...` trigger.

- `plugins/research-partner/skills/*/SKILL.md`
  - Rewrite every frontmatter description to start with a clear `Use when...` trigger.
  - Update `plugins/research-partner/skills/research-partner/SKILL.md` so it names the new `run` command as the default orchestration path.

- `plugins/research-partner/scripts/research_partner.py`
  - Add real lane execution functions.
  - Add `run_review()` orchestration.
  - Add a `run` CLI subcommand.
  - Tighten bundle provenance so same-title findings from different lanes retain lane source.

- `tests/test_plugins_and_agents.py`
  - Add tests for required interface URLs.
  - Add tests for trigger-style descriptions.
  - Add tests for `research-partner run`.
  - Add tests that lane finding provenance is retained.

Create:

- `plugins/documentation-wizard/tests/test_documentation_wizard.py`
- `plugins/research-partner/tests/test_research_partner.py`
- `plugins/workspace-governor/tests/test_workspace_governor.py`

These plugin-local tests can import and reuse selected root-level tests. Their purpose is to satisfy plugin-local evaluation and make each plugin independently testable.

Do not create new frameworks, dependencies, plugin manifests, or fallback paths.

---

### Task 0: Create The OpenAI/Codex Source Repo Layout

**Files:**
- Create: `/Users/ncamarda/Projects/codex-personal-plugins/`
- Create: `.gitignore`
- Create: `AGENTS.md`
- Create: `.agents/plugins/marketplace.json`
- Move: `documentation-wizard/` to `plugins/documentation-wizard/`
- Move: `research-partner/` to `plugins/research-partner/`
- Move: `workspace-governor/` to `plugins/workspace-governor/`
- Move: `scripts/` to `scripts/`
- Move: `tests/` to `tests/`
- Move: `docs/` to `docs/`
- Move: `three-plugin-assessment.md` to `three-plugin-assessment.md`

- [ ] **Step 1: Create the source repo directory**

Run:

```bash
mkdir -p /Users/ncamarda/Projects/codex-personal-plugins/plugins
```

Expected: directory exists.

- [ ] **Step 2: Copy authored source from the personal install workspace**

Run:

```bash
rsync -a --delete /Users/ncamarda/.codex/plugins/documentation-wizard/ /Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/
rsync -a --delete /Users/ncamarda/.codex/plugins/research-partner/ /Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/
rsync -a --delete /Users/ncamarda/.codex/plugins/workspace-governor/ /Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/
rsync -a /Users/ncamarda/.codex/plugins/scripts/ /Users/ncamarda/Projects/codex-personal-plugins/scripts/
rsync -a /Users/ncamarda/.codex/plugins/tests/ /Users/ncamarda/Projects/codex-personal-plugins/tests/
rsync -a /Users/ncamarda/.codex/plugins/docs/ /Users/ncamarda/Projects/codex-personal-plugins/docs/
cp /Users/ncamarda/.codex/plugins/three-plugin-assessment.md /Users/ncamarda/Projects/codex-personal-plugins/three-plugin-assessment.md
```

Expected: only authored plugin source, shared tests, shared scripts, docs, and the assessment file are copied. Do not copy `/Users/ncamarda/.codex/plugins/cache`.

- [ ] **Step 3: Create `.gitignore`**

Create `/Users/ncamarda/Projects/codex-personal-plugins/.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.coverage
coverage.xml
htmlcov/
node_modules/
.DS_Store
*.log
*.tmp
*.temp
/tmp/
/cache/
/.remote-plugin-install-staging/
/plugin-eval-report.html
*.plugin-eval.md
```

- [ ] **Step 4: Create repo-local `AGENTS.md`**

Create `/Users/ncamarda/Projects/codex-personal-plugins/AGENTS.md`:

```markdown
# Codex Personal Plugins

## Source of truth

This repository is the source of truth for personally authored Codex plugins.
Do not edit installed copies under `~/.codex/plugins/<plugin-name>` except through the deploy script.

## Layout

- Repo marketplace: `.agents/plugins/marketplace.json`
- Authored plugins: `plugins/<plugin-name>/`
- Personal install target: `~/.codex/plugins/<plugin-name>/`
- Shared tests: `tests/`
- Shared deployment helpers: `scripts/`
- Implementation plans and results: `docs/superpowers/plans/`

## Development rules

- Keep plugin manifests, skill descriptions, helper CLIs, tests, and docs in git.
- Do not commit Codex cache directories, installed curated plugins, generated reports, or Python cache files.
- Run root tests and plugin-local tests before considering work complete.
- After source changes, deploy into `~/.codex/plugins` with `python scripts/deploy_plugins.py install --source-root . --home ~`.
- For research and analysis plugin behavior, distinguish data reality, method validity, implementation behavior, and scientific interpretation.
```

- [ ] **Step 5: Create repo marketplace**

Create `/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json`:

```json
{
  "name": "codex-personal-plugins",
  "interface": {
    "displayName": "Codex Personal Plugins"
  },
  "plugins": [
    {
      "name": "documentation-wizard",
      "source": {
        "source": "local",
        "path": "./plugins/documentation-wizard"
      },
      "policy": {
        "installation": "INSTALLED_BY_DEFAULT",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    },
    {
      "name": "research-partner",
      "source": {
        "source": "local",
        "path": "./plugins/research-partner"
      },
      "policy": {
        "installation": "INSTALLED_BY_DEFAULT",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    },
    {
      "name": "workspace-governor",
      "source": {
        "source": "local",
        "path": "./plugins/workspace-governor"
      },
      "policy": {
        "installation": "INSTALLED_BY_DEFAULT",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

- [ ] **Step 6: Initialize git**

Run:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
git init
git remote add origin https://github.com/nicholas-camarda/codex-personal-plugins.git
git status --short
```

Expected: `git status --short` shows only source repo files, not `cache/` or curated plugins. `git remote -v` should show `origin` pointing at `https://github.com/nicholas-camarda/codex-personal-plugins.git`.

- [ ] **Step 7: Run tests from the new source root**

Run:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
python -m unittest tests/test_plugins_and_agents.py
```

Expected: tests may fail at this point if imports still assume plugin roots at repo top level. That failure is acceptable and is fixed in Task 0.1.

- [ ] **Step 8: Do not commit the intermediate layout if tests fail**

If Step 7 failed because tests still point at the old top-level plugin paths, leave the files unstaged and continue to Task 0.1. The first commit for the new repo layout happens after Task 0.1 passes.

---

### Task 0.1: Update Shared Tests And Deploy Script For Repo Marketplace Layout

**Files:**
- Modify: `tests/test_plugins_and_agents.py`
- Modify: `scripts/deploy_plugins.py`

- [ ] **Step 1: Add path constants to tests**

In `tests/test_plugins_and_agents.py`, after `ROOT = Path(__file__).resolve().parents[1]`, add:

```python
PLUGINS_ROOT = ROOT / "plugins"
```

Replace test helper module paths:

```python
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
```

- [ ] **Step 2: Update staged install helper**

Replace `stage_home_workspace()` with:

```python
    def stage_home_workspace(self, home_root: Path) -> Path:
        source_root = home_root / "source" / "codex-personal-plugins"
        source_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "plugins", source_root / "plugins")
        shutil.copytree(ROOT / "scripts", source_root / "scripts")
        shutil.copytree(ROOT / ".agents", source_root / ".agents")
        return source_root
```

Replace `install_plugins_for_test()` with:

```python
    def install_plugins_for_test(self, home_root: Path) -> dict:
        source_root = self.stage_home_workspace(home_root)
        return DEPLOY_PLUGINS.install_plugins(
            source_root=source_root,
            home_root=home_root,
            run_validate=True,
        )
```

- [ ] **Step 3: Update direct file references in tests**

Replace references to `ROOT / name` for plugin roots with `PLUGINS_ROOT / name`.

Use this exact replacement in `test_deploy_plugins_installs_home_marketplace_and_validates()`:

```python
            source_root = self.stage_home_workspace(home_root)

            payload = DEPLOY_PLUGINS.install_plugins(
                source_root=source_root,
                home_root=home_root,
                run_validate=True,
            )
```

- [ ] **Step 4: Update deploy plugin discovery**

In `scripts/deploy_plugins.py`, change `discover_plugins()` to discover from `source_root / "plugins"`:

```python
def discover_plugins(source_root: Path) -> list[dict[str, Any]]:
    plugin_parent = source_root / "plugins"
    plugins: list[dict[str, Any]] = []
    for child in sorted(plugin_parent.iterdir(), key=lambda path: path.name):
        manifest_path = child / ".codex-plugin" / "plugin.json"
        if not manifest_path.exists():
            continue
        manifest = load_json(manifest_path)
        name = manifest.get("name")
        if not isinstance(name, str):
            raise ValueError(f"{manifest_path} is missing a plugin name")
        plugins.append(
            {
                "name": name,
                "root": child.resolve(),
                "manifest": manifest,
                "script": (child / "scripts" / plugin_script_name(name)).resolve(),
                "category": manifest.get("interface", {}).get("category", "Productivity"),
            }
        )
    if not plugins:
        raise ValueError(f"No plugins discovered under {plugin_parent}")
    return plugins
```

- [ ] **Step 5: Add copy helper to deploy script**

Add after `expected_home_workspace_root()`:

```python
def copy_plugin_to_home(plugin: dict[str, Any], install_root: Path, dry_run: bool = False) -> Path:
    destination = install_root / plugin["name"]
    if dry_run:
        return destination
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(plugin["root"], destination)
    return destination
```

Add `import shutil` near the top of `scripts/deploy_plugins.py`.

- [ ] **Step 6: Update marketplace payload builder call**

In `install_plugins()`, remove the source-root equality check:

```python
    install_root = expected_home_workspace_root(home_root)
```

Delete this block:

```python
    if source_root != install_root:
        raise ValueError(
            "source_root must be the home plugin workspace "
            f"({install_root}) so there is only one plugin source tree"
        )
```

After `plugins = select_plugins(...)`, copy selected plugins and update each validation script path:

```python
    plugins = select_plugins(discover_plugins(source_root), plugin_names)
    for plugin in plugins:
        installed_root = copy_plugin_to_home(plugin, install_root, dry_run=dry_run)
        plugin["installed_root"] = installed_root
        plugin["script"] = (installed_root / "scripts" / plugin_script_name(plugin["name"])).resolve()
```

Keep marketplace paths as:

```python
path_builder=lambda plugin: f"./.codex/plugins/{plugin['name']}",
```

- [ ] **Step 7: Run tests**

Run:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
python -m unittest tests/test_plugins_and_agents.py
```

Expected: existing tests pass after the path migration changes.

- [ ] **Step 8: Commit**

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
git add .gitignore AGENTS.md .agents/plugins/marketplace.json plugins scripts tests docs three-plugin-assessment.md
git commit -m "chore: create codex plugin source repo"
```

---

### Task 0.2: Audit For Conflicting Plugin Definitions And Stale Installs

**Files:**
- Create: `docs/superpowers/audits/plugin-source-audit.md`
- No deletions in this task.

- [ ] **Step 1: Inventory plugin definitions under `~/Projects` and personal installs**

Run:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
mkdir -p docs/superpowers/audits
{
  printf '# Codex Plugin Source Audit\n\n'
  printf '## Expected Source Of Truth\n\n'
  printf -- '- `/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json`\n'
  printf -- '- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/.codex-plugin/plugin.json`\n'
  printf -- '- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/.codex-plugin/plugin.json`\n'
  printf -- '- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/.codex-plugin/plugin.json`\n'
  printf -- '- Installed copies under `/Users/ncamarda/.codex/plugins/<plugin-name>/` are deploy targets, not source.\n\n'
  printf '## Project Plugin Definitions\n\n'
  find /Users/ncamarda/Projects \
    \( -path '*/.git' -o -path '*/node_modules' -o -path '*/__pycache__' -o -path '*/.venv' \) -prune -o \
    -type f \( -path '*/.codex-plugin/plugin.json' -o -path '*/.agents/plugins/marketplace.json' -o -name 'SKILL.md' \) \
    -print | sort
  printf '\n## Personal Install Definitions\n\n'
  find /Users/ncamarda/.codex/plugins \
    \( -path '/Users/ncamarda/.codex/plugins/cache' -o -path '*/__pycache__' \) -prune -o \
    -type f \( -path '*/.codex-plugin/plugin.json' -o -path '*/.agents/plugins/marketplace.json' -o -name 'SKILL.md' \) \
    -print | sort
} > docs/superpowers/audits/plugin-source-audit.md
```

Expected: `docs/superpowers/audits/plugin-source-audit.md` exists and lists every local marketplace, plugin manifest, and skill definition found in source and install locations.

- [ ] **Step 2: Review the audit for conflicting authored plugin definitions**

Run:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
rg -n "documentation-wizard|research-partner|workspace-governor|marketplace.json|SKILL.md" docs/superpowers/audits/plugin-source-audit.md
```

Expected allowed source paths:

```text
/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/assess-literature-support/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/design-robustness-tests/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/research-partner/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-documentation-consistency/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-implementation-validity/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-statistical-validity/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/synthesize-review/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/skills/workspace-governor/SKILL.md
```

Expected allowed install paths:

```text
/Users/ncamarda/.codex/plugins/documentation-wizard/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/research-partner/skills/assess-literature-support/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/design-robustness-tests/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/research-partner/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-documentation-consistency/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-implementation-validity/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-statistical-validity/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/synthesize-review/SKILL.md
/Users/ncamarda/.codex/plugins/workspace-governor/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/workspace-governor/skills/workspace-governor/SKILL.md
```

Any authored `documentation-wizard`, `research-partner`, or `workspace-governor` manifest or skill path outside those lists is a conflict that must be resolved before continuing.

- [ ] **Step 3: Run the conflict detector**

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
python - <<'PY'
from pathlib import Path

audit = Path("docs/superpowers/audits/plugin-source-audit.md")
allowed = {
    "/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/.codex-plugin/plugin.json",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/.codex-plugin/plugin.json",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/assess-literature-support/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/design-robustness-tests/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/research-partner/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-documentation-consistency/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-implementation-validity/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-statistical-validity/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/synthesize-review/SKILL.md",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/.codex-plugin/plugin.json",
    "/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/skills/workspace-governor/SKILL.md",
    "/Users/ncamarda/.codex/plugins/documentation-wizard/.codex-plugin/plugin.json",
    "/Users/ncamarda/.codex/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/.codex-plugin/plugin.json",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/assess-literature-support/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/design-robustness-tests/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/research-partner/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/review-documentation-consistency/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/review-implementation-validity/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/review-statistical-validity/SKILL.md",
    "/Users/ncamarda/.codex/plugins/research-partner/skills/synthesize-review/SKILL.md",
    "/Users/ncamarda/.codex/plugins/workspace-governor/.codex-plugin/plugin.json",
    "/Users/ncamarda/.codex/plugins/workspace-governor/skills/workspace-governor/SKILL.md",
}
interesting_names = ("documentation-wizard", "research-partner", "workspace-governor")
conflicts = []
for raw_line in audit.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line.startswith("/"):
        continue
    if not any(name in line for name in interesting_names):
        continue
    if line not in allowed:
        conflicts.append(line)

if conflicts:
    print("Conflicting authored plugin definitions found:")
    for path in conflicts:
        print(path)
    raise SystemExit(1)
print("No conflicting authored plugin definitions found.")
PY
```

Expected: prints `No conflicting authored plugin definitions found.` If this command fails, stop the plan and investigate each duplicate or stale authored plugin definition. If a stale copy contains useful information, merge that information into the canonical source plugin under `/Users/ncamarda/Projects/codex-personal-plugins/plugins/<plugin-name>/`. After useful information is merged, remove the stale duplicate definition from the workspace so it cannot pollute Codex discovery or future audits. Do not leave old plugin manifests, marketplace entries, or skill definitions lying around as alternate sources of truth.

- [ ] **Step 4: Record the cleanup decision**

Append a cleanup section:

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
{
  printf '\n## Cleanup Decision\n\n'
  printf 'Allowed source repo: `/Users/ncamarda/Projects/codex-personal-plugins`.\n'
  printf 'Allowed remote: `https://github.com/nicholas-camarda/codex-personal-plugins.git`.\n'
  printf 'Allowed personal install roots: `/Users/ncamarda/.codex/plugins/documentation-wizard`, `/Users/ncamarda/.codex/plugins/research-partner`, `/Users/ncamarda/.codex/plugins/workspace-governor`.\n'
  printf 'No curated cache files are source of truth.\n'
  printf 'Duplicate authored plugin definitions must be merged into canonical source if useful, then removed from discovery paths.\n'
  printf 'Conflict detector passed before implementation continued.\n'
} >> docs/superpowers/audits/plugin-source-audit.md
```

- [ ] **Step 5: Commit the audit**

```bash
cd /Users/ncamarda/Projects/codex-personal-plugins
git add docs/superpowers/audits/plugin-source-audit.md
git commit -m "docs: audit codex plugin source definitions"
```

---

### Task 1: Add Tests For Manifest Interface URLs

**Files:**
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add the failing test**

Insert this test method inside `class PluginRegressionTests(unittest.TestCase):`, after `install_plugins_for_test()`:

```python
    def test_plugin_manifests_have_required_interface_urls(self) -> None:
        for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]:
            manifest_path = PLUGINS_ROOT / plugin_name / ".codex-plugin" / "plugin.json"
            manifest = DEPLOY_PLUGINS.load_json(manifest_path)
            interface = manifest.get("interface", {})
            for key in ["websiteURL", "privacyPolicyURL", "termsOfServiceURL"]:
                value = interface.get(key)
                self.assertIsInstance(value, str, f"{plugin_name} missing interface.{key}")
                self.assertTrue(value.startswith("https://github.com/nicholas-camarda/codex-personal-plugins"), f"{plugin_name} has non-project URL for {key}")
                self.assertNotIn("example.com", value)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_plugin_manifests_have_required_interface_urls -v
```

Expected: FAIL because the three manifests do not yet define all required interface URLs.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_plugins_and_agents.py
git commit -m "test: require plugin interface urls"
```

---

### Task 2: Add Real Interface URLs To Plugin Manifests

**Files:**
- Modify: `plugins/documentation-wizard/.codex-plugin/plugin.json`
- Modify: `plugins/research-partner/.codex-plugin/plugin.json`
- Modify: `plugins/workspace-governor/.codex-plugin/plugin.json`

- [ ] **Step 1: Update `documentation-wizard` manifest**

In `plugins/documentation-wizard/.codex-plugin/plugin.json`, add these keys inside `interface` after `longDescription`:

```json
    "websiteURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "privacyPolicyURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "termsOfServiceURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
```

- [ ] **Step 2: Update `research-partner` manifest**

In `plugins/research-partner/.codex-plugin/plugin.json`, add these keys inside `interface` after `longDescription`:

```json
    "websiteURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "privacyPolicyURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "termsOfServiceURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
```

- [ ] **Step 3: Update `workspace-governor` manifest**

In `plugins/workspace-governor/.codex-plugin/plugin.json`, add these keys inside `interface` after `longDescription`:

```json
    "websiteURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "privacyPolicyURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
    "termsOfServiceURL": "https://github.com/nicholas-camarda/codex-personal-plugins",
```

- [ ] **Step 4: Run the manifest test**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_plugin_manifests_have_required_interface_urls -v
```

Expected: PASS.

- [ ] **Step 5: Run plugin validates**

Run:

```bash
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
```

Expected: each command returns JSON with `"passed": true`.

- [ ] **Step 6: Commit**

```bash
git add plugins/documentation-wizard/.codex-plugin/plugin.json plugins/research-partner/.codex-plugin/plugin.json plugins/workspace-governor/.codex-plugin/plugin.json
git commit -m "fix: add required plugin interface urls"
```

---

### Task 3: Add Tests For Skill Trigger Descriptions

**Files:**
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add helper and failing test**

Insert this helper near `load_module()`:

```python
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
```

Insert this test method inside `PluginRegressionTests`:

```python
    def test_skill_descriptions_use_clear_trigger_language(self) -> None:
        skill_paths = sorted(
            path
            for plugin_name in ["documentation-wizard", "research-partner", "workspace-governor"]
            for path in (ROOT / plugin_name / "skills").glob("*/SKILL.md")
        )
        self.assertGreater(len(skill_paths), 0)
        for skill_path in skill_paths:
            description = read_skill_description(skill_path)
            self.assertTrue(
                description.startswith("Use when "),
                f"{skill_path.relative_to(ROOT)} description should start with 'Use when '",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_skill_descriptions_use_clear_trigger_language -v
```

Expected: FAIL for most current skill descriptions.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_plugins_and_agents.py
git commit -m "test: require trigger-oriented skill descriptions"
```

---

### Task 4: Rewrite Skill Descriptions And Align Research Partner Contract

**Files:**
- Modify: `plugins/documentation-wizard/skills/documentation-wizard/SKILL.md`
- Modify: `plugins/workspace-governor/skills/workspace-governor/SKILL.md`
- Modify: every `plugins/research-partner/skills/*/SKILL.md`

- [ ] **Step 1: Replace `documentation-wizard` frontmatter description**

Use this exact frontmatter description:

```yaml
description: Use when documentation must be checked against the current code, CLI flags, schemas, paths, or public/private documentation contract.
```

- [ ] **Step 2: Replace `workspace-governor` frontmatter description**

Use this exact frontmatter description:

```yaml
description: Use when workspace paths, canonical research layout, public/private docs, migration plans, or publish previews need audit or verification.
```

- [ ] **Step 3: Replace `research-partner` skill descriptions**

Use these exact descriptions:

```yaml
# plugins/research-partner/skills/assess-literature-support/SKILL.md
description: Use when method choices need literature and practical support assessed against the actual scientific question, data, and implementation.

# plugins/research-partner/skills/design-robustness-tests/SKILL.md
description: Use when an analysis needs tests that catch scientifically meaningful implementation, estimand, data, or artifact regressions.

# plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
description: Use when analysis inputs, outputs, code paths, runtime artifacts, and published outputs must be reconstructed before review.

# plugins/research-partner/skills/research-partner/SKILL.md
description: Use when a research analysis, manuscript claim, repository, or pipeline needs a data-first multi-lane review grounded in local artifacts.

# plugins/research-partner/skills/review-documentation-consistency/SKILL.md
description: Use when manuscripts, READMEs, methods prose, or operational docs must be checked against live code, schemas, and paths.

# plugins/research-partner/skills/review-implementation-validity/SKILL.md
description: Use when code must be checked against the claimed method, target estimand, generated outputs, and repository workflow.

# plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
description: Use when claims, interpretation, bias, or generalizability must be reviewed against the actual cohort, design, and measurements.

# plugins/research-partner/skills/review-statistical-validity/SKILL.md
description: Use when statistical methods must be checked against the actual design, data structure, outcome, and claimed question.

# plugins/research-partner/skills/synthesize-review/SKILL.md
description: Use when specialist lane outputs need to be merged into one ranked final review with evidence and disagreements preserved.
```

- [ ] **Step 4: Update `plugins/research-partner/skills/research-partner/SKILL.md` default command language**

Add this paragraph under `# Purpose`:

```markdown
Default to `scripts/research_partner.py run --repo <repo> --output-dir <dir>` for end-to-end review execution. Use `inventory` only when the user explicitly wants preflight without lane execution, and use `bundle` only when lane JSON files were produced elsewhere.
```

- [ ] **Step 5: Run trigger description test**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_skill_descriptions_use_clear_trigger_language -v
```

Expected: PASS.

- [ ] **Step 6: Run full tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Expected: 18 or more tests pass, depending on prior task count.

- [ ] **Step 7: Commit**

```bash
git add plugins/documentation-wizard/skills/documentation-wizard/SKILL.md plugins/workspace-governor/skills/workspace-governor/SKILL.md plugins/research-partner/skills
git commit -m "docs: clarify skill trigger descriptions"
```

---

### Task 5: Add Tests For Research Partner Lane Execution

**Files:**
- Modify: `tests/test_plugins_and_agents.py`

- [ ] **Step 1: Add failing direct function test**

Insert this test inside `PluginRegressionTests`:

```python
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
```

- [ ] **Step 2: Add failing CLI smoke test**

Insert this test inside `PluginRegressionTests`:

```python
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
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
python -m unittest \
  tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_run_executes_actual_lanes \
  tests.test_plugins_and_agents.PluginRegressionTests.test_installed_research_partner_run_executes_lanes -v
```

Expected: FAIL because `run_review` and the `run` command do not exist yet.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_plugins_and_agents.py
git commit -m "test: require research partner lane execution"
```

---

### Task 6: Implement Research Partner Lane Execution

**Files:**
- Modify: `plugins/research-partner/scripts/research_partner.py`

- [ ] **Step 1: Add lane constants**

Add this after `DEFAULT_FLOW`:

```python
EXECUTABLE_LANES = [
    "documentation-wizard",
    "implementation-auditor",
    "stats-reviewer",
    "scientific-reviewer",
    "literature-support-reviewer",
    "robustness-test-designer",
]
```

- [ ] **Step 2: Add JSON writer and lane payload helper**

Add these functions after `load_json()`:

```python
def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def lane_payload(
    *,
    lane: str,
    root: Path,
    artifact_map: dict[str, Any],
    findings: list[dict[str, Any]],
    required_tests_checks: list[str],
    recommended_actions: list[str],
    direct_evidence_vs_inference: str,
) -> dict[str, Any]:
    return {
        "scope": "research-review-lane",
        "lane": lane,
        "artifact_map": {"repo_root": str(root), **artifact_map},
        "findings": findings,
        "direct_evidence_vs_inference": direct_evidence_vs_inference,
        "required_tests_checks": required_tests_checks,
        "recommended_actions": recommended_actions,
    }
```

- [ ] **Step 3: Add documentation lane execution**

Add this function after `run_workspace_governor_dry_run()`:

```python
def run_documentation_wizard_lane(root: Path) -> dict[str, Any]:
    script = peer_plugin_script("documentation-wizard", "documentation_wizard.py")
    if not script.exists():
        return lane_payload(
            lane="documentation-wizard",
            root=root,
            artifact_map={"documentation_wizard_script": str(script)},
            findings=[
                {
                    "title": "Documentation lane helper unavailable",
                    "severity": "P1",
                    "evidence_basis": "Missing",
                    "message": "The documentation-wizard helper script was not found, so documentation consistency was not executed.",
                    "lane": "documentation-wizard",
                }
            ],
            required_tests_checks=["Restore documentation-wizard installation and rerun research-partner."],
            recommended_actions=["Install or repair documentation-wizard before accepting documentation consistency conclusions."],
            direct_evidence_vs_inference="This lane reports missing execution evidence because the sibling helper was unavailable.",
        )
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "report", "--repo", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise ValueError("documentation-wizard returned a non-object payload")
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError, ValueError) as exc:
        return lane_payload(
            lane="documentation-wizard",
            root=root,
            artifact_map={"documentation_wizard_script": str(script)},
            findings=[
                {
                    "title": "Documentation lane execution failed",
                    "severity": "P1",
                    "evidence_basis": "Direct",
                    "message": f"documentation-wizard failed during report execution: {exc}",
                    "lane": "documentation-wizard",
                }
            ],
            required_tests_checks=["Run documentation-wizard report directly and fix the execution error."],
            recommended_actions=["Do not treat documentation consistency as reviewed until documentation-wizard runs successfully."],
            direct_evidence_vs_inference="This lane is grounded in the failed subprocess invocation.",
        )

    findings = []
    for finding in payload.get("findings", []):
        if isinstance(finding, dict):
            enriched = dict(finding)
            enriched.setdefault("title", enriched.get("kind", "Documentation finding"))
            enriched.setdefault("severity", "P2")
            enriched.setdefault("evidence_basis", "Direct")
            enriched["lane"] = "documentation-wizard"
            findings.append(enriched)
    return lane_payload(
        lane="documentation-wizard",
        root=root,
        artifact_map={
            "documentation_wizard_script": str(script),
            "documentation_report_scope": payload.get("scope"),
            "documentation_artifact_map": payload.get("artifact_map", {}),
        },
        findings=findings,
        required_tests_checks=list(payload.get("required_tests_checks", [])),
        recommended_actions=list(payload.get("recommended_actions", [])),
        direct_evidence_vs_inference=str(payload.get("direct_evidence_vs_inference", "Documentation findings are grounded in documentation-wizard output.")),
    )
```

- [ ] **Step 4: Add local heuristic lane functions**

Add these functions after `run_documentation_wizard_lane()`:

```python
def _repo_files(root: Path, suffixes: set[str]) -> list[str]:
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name.lower() not in IGNORED_WALK_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() in suffixes:
                paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def implementation_auditor_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    scripts = list(preflight.get("artifact_map", {}).get("scripts_and_tests", []))
    test_files = [path for path in scripts if "/tests/" in f"/{path}" or path.startswith("tests/") or Path(path).name.startswith("test_")]
    code_files = [path for path in scripts if path.endswith((".py", ".R", ".r", ".sh")) and path not in test_files]
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if code_files and not test_files:
        findings.append(
            {
                "title": "Executable analysis code lacks discovered tests",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "Preflight found scripts but no test files, so implementation validity is weakly protected.",
                "lane": "implementation-auditor",
            }
        )
        actions.append("Add tests or smoke checks for the executable analysis scripts before trusting implementation claims.")
    return lane_payload(
        lane="implementation-auditor",
        root=root,
        artifact_map={"code_files": code_files, "test_files": test_files},
        findings=findings,
        required_tests_checks=["Run the analysis smoke command and the repository test suite, if present."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane is grounded in files discovered by preflight; method correctness still requires manual code review.",
    )


def stats_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    analysis_files = _repo_files(root, {".py", ".r", ".R", ".qmd", ".ipynb"})
    text = "\n".join(read_text(root / path) for path in analysis_files if not path.endswith(".ipynb"))
    method_terms = sorted(set(re.findall(r"\b(cox|logistic|linear|regression|bootstrap|kaplan|survival|auc|calibration|pvalue|p-value)\b", text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if analysis_files and not method_terms:
        findings.append(
            {
                "title": "Statistical method target is not explicit in code text",
                "severity": "P3",
                "evidence_basis": "Inference",
                "message": "Analysis files were present, but the lightweight scan did not find explicit statistical method terms.",
                "lane": "stats-reviewer",
            }
        )
        actions.append("Identify the estimand or prediction target and verify the statistical method manually.")
    return lane_payload(
        lane="stats-reviewer",
        root=root,
        artifact_map={"analysis_files": analysis_files, "method_terms": method_terms},
        findings=findings,
        required_tests_checks=["Check estimand alignment, outcome type, missingness handling, calibration, and sensitivity analyses."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane uses a lightweight repository scan and flags missing evidence; it does not replace a full statistical review.",
    )


def scientific_reviewer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    doc_files = _repo_files(root, {".md", ".mdx", ".rst", ".txt", ".qmd"})
    text = "\n".join(read_text(root / path) for path in doc_files)
    causal_terms = sorted(set(re.findall(r"\b(causes?|causal|effect|impact|proves?|predicts?|prognostic)\b", text, flags=re.I)))
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if causal_terms:
        findings.append(
            {
                "title": "Interpretive claim language needs design support check",
                "severity": "P2",
                "evidence_basis": "Direct",
                "message": "Public or project docs include causal, predictive, or prognostic language that must be checked against design and validation evidence.",
                "lane": "scientific-reviewer",
            }
        )
        actions.append("Classify each claim as descriptive, associational, causal, predictive, or prognostic before reporting it.")
    return lane_payload(
        lane="scientific-reviewer",
        root=root,
        artifact_map={"doc_files": doc_files, "claim_terms": causal_terms},
        findings=findings,
        required_tests_checks=["Verify cohort definition, measurement validity, bias risks, and external validity before accepting interpretation."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane is grounded in local prose and flags claim language that requires scientific interpretation review.",
    )


def literature_support_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    registry_path = preflight.get("artifact_map", {}).get("analysis_registry")
    findings: list[dict[str, Any]] = []
    actions: list[str] = []
    if registry_path is None:
        findings.append(
            {
                "title": "Literature support context is under-specified",
                "severity": "P3",
                "evidence_basis": "Missing",
                "message": "No analysis_registry.yaml was discovered, so domain and method context for literature support is incomplete.",
                "lane": "literature-support-reviewer",
            }
        )
        actions.append("Add or update analysis_registry.yaml with project type, domain, and analysis context before literature support review.")
    return lane_payload(
        lane="literature-support-reviewer",
        root=root,
        artifact_map={"analysis_registry": registry_path},
        findings=findings,
        required_tests_checks=["Tie any literature citation to the actual design, population, endpoint, and implementation details."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane checks whether enough local context exists for a literature support review; it does not perform external literature search.",
    )


def robustness_test_designer_lane(root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    scripts = list(preflight.get("artifact_map", {}).get("scripts_and_tests", []))
    findings: list[dict[str, Any]] = []
    actions = [
        "Add regression tests for artifact presence, schema stability, documented path assumptions, and one representative analysis smoke run."
    ]
    if scripts:
        findings.append(
            {
                "title": "Robustness test targets identified",
                "severity": "P3",
                "evidence_basis": "Direct",
                "message": "Executable files were found and should be covered by smoke or regression tests tied to scientific failure modes.",
                "lane": "robustness-test-designer",
            }
        )
    return lane_payload(
        lane="robustness-test-designer",
        root=root,
        artifact_map={"scripts_and_tests": scripts},
        findings=findings,
        required_tests_checks=["Add at least one failure-mode test for stale paths, stale artifacts, and output schema drift."],
        recommended_actions=actions,
        direct_evidence_vs_inference="This lane derives test targets from preflight inventory and the repository tree.",
    )
```

- [ ] **Step 5: Add dispatcher and `run_review()`**

Add this after `robustness_test_designer_lane()`:

```python
def execute_lane(lane: str, root: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    if lane == "documentation-wizard":
        return run_documentation_wizard_lane(root)
    if lane == "implementation-auditor":
        return implementation_auditor_lane(root, preflight)
    if lane == "stats-reviewer":
        return stats_reviewer_lane(root, preflight)
    if lane == "scientific-reviewer":
        return scientific_reviewer_lane(root, preflight)
    if lane == "literature-support-reviewer":
        return literature_support_lane(root, preflight)
    if lane == "robustness-test-designer":
        return robustness_test_designer_lane(root, preflight)
    raise ValueError(f"Unknown lane: {lane}")


def run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    selected_lanes = lanes or EXECUTABLE_LANES
    unknown = sorted(set(selected_lanes) - set(EXECUTABLE_LANES))
    if unknown:
        raise ValueError(f"Unknown lanes requested: {', '.join(unknown)}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = inventory_repo(root)
    preflight_path = output_dir / "preflight.json"
    write_json(preflight_path, preflight)

    lane_paths: list[Path] = []
    lane_outputs: list[dict[str, Any]] = []
    for lane in selected_lanes:
        payload = execute_lane(lane, root, preflight)
        lane_path = output_dir / f"{lane}.json"
        write_json(lane_path, payload)
        lane_paths.append(lane_path)
        lane_outputs.append({"lane": lane, "path": str(lane_path), "finding_count": len(payload.get("findings", []))})

    bundle = bundle_review(preflight_path, lane_paths)
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
```

- [ ] **Step 6: Add `run` subcommand**

In `main()`, add parser setup after the `bundle` parser:

```python
    run_parser = subparsers.add_parser("run", help="Run preflight, execute review lanes, and bundle results")
    run_parser.add_argument("--repo", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--lane", action="append", default=[])
```

Change the command dispatch to:

```python
    if args.command == "inventory":
        payload = inventory_repo(Path(args.repo).expanduser().resolve())
    elif args.command == "bundle":
        payload = bundle_review(Path(args.preflight).resolve(), [Path(item).resolve() for item in args.lane])
    elif args.command == "run":
        payload = run_review(
            repo_root=Path(args.repo),
            output_dir=Path(args.output_dir),
            lanes=args.lane or None,
        )
    else:
        payload = validate_plugin(Path(__file__).resolve().parent)
```

- [ ] **Step 7: Run lane execution tests**

Run:

```bash
python -m unittest \
  tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_run_executes_actual_lanes \
  tests.test_plugins_and_agents.PluginRegressionTests.test_installed_research_partner_run_executes_lanes -v
```

Expected: PASS.

- [ ] **Step 8: Run full tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add plugins/research-partner/scripts/research_partner.py tests/test_plugins_and_agents.py
git commit -m "feat: execute research partner review lanes"
```

---

### Task 7: Preserve Lane Provenance During Bundling

**Files:**
- Modify: `tests/test_plugins_and_agents.py`
- Modify: `plugins/research-partner/scripts/research_partner.py`

- [ ] **Step 1: Add failing test**

Insert this test inside `PluginRegressionTests`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_bundle_preserves_lane_provenance_for_same_title -v
```

Expected: FAIL because current `finding_key()` deduplicates by title/message only.

- [ ] **Step 3: Update `finding_key()`**

Replace `finding_key()` with:

```python
def finding_key(finding: dict[str, Any]) -> tuple[Any, ...]:
    return (
        finding.get("lane"),
        finding.get("title") or finding.get("message"),
    )
```

- [ ] **Step 4: Run provenance test**

Run:

```bash
python -m unittest tests.test_plugins_and_agents.PluginRegressionTests.test_research_partner_bundle_preserves_lane_provenance_for_same_title -v
```

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugins/research-partner/scripts/research_partner.py tests/test_plugins_and_agents.py
git commit -m "fix: preserve review lane provenance"
```

---

### Task 8: Add Plugin-Local Test Entry Points

**Files:**
- Create: `plugins/documentation-wizard/tests/test_documentation_wizard.py`
- Create: `plugins/research-partner/tests/test_research_partner.py`
- Create: `plugins/workspace-governor/tests/test_workspace_governor.py`

- [ ] **Step 1: Create documentation-wizard local tests**

Create `plugins/documentation-wizard/tests/test_documentation_wizard.py`:

```python
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent


def load_module():
    module_path = ROOT / "scripts" / "documentation_wizard.py"
    spec = importlib.util.spec_from_file_location("documentation_wizard_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DOCUMENTATION_WIZARD = load_module()


class DocumentationWizardLocalTests(unittest.TestCase):
    def test_report_smoke_on_generic_fixture(self) -> None:
        report = DOCUMENTATION_WIZARD.build_report(WORKSPACE_ROOT / "tests" / "fixtures" / "generic_python_repo")
        self.assertEqual(report["scope"], "documentation-drift-audit")
        self.assertIsInstance(report["findings"], list)

    def test_iter_files_prunes_non_public_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs" / "guide.md").parent.mkdir(parents=True)
            (root / "docs" / "guide.md").write_text("public\n", encoding="utf-8")
            (root / "docs" / "archive" / "old.md").parent.mkdir(parents=True)
            (root / "docs" / "archive" / "old.md").write_text("archived\n", encoding="utf-8")
            files = DOCUMENTATION_WIZARD.iter_files(root, {".md"})
        self.assertEqual([path.relative_to(root).as_posix() for path in files], ["docs/guide.md"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Create research-partner local tests**

Create `plugins/research-partner/tests/test_research_partner.py`:

```python
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent


def load_module():
    module_path = ROOT / "scripts" / "research_partner.py"
    spec = importlib.util.spec_from_file_location("research_partner_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESEARCH_PARTNER = load_module()


class ResearchPartnerLocalTests(unittest.TestCase):
    def test_inventory_smoke_on_minimal_fixture(self) -> None:
        report = RESEARCH_PARTNER.inventory_repo(WORKSPACE_ROOT / "tests" / "fixtures" / "minimal_repo")
        self.assertEqual(report["scope"], "analysis-review-preflight")
        self.assertIn("flow", report)

    def test_run_review_executes_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "review"
            report = RESEARCH_PARTNER.run_review(WORKSPACE_ROOT / "tests" / "fixtures" / "research_repo", output_dir)
        self.assertEqual(report["command"], "run")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(len(report["lane_outputs"]), 6)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Create workspace-governor local tests**

Create `plugins/workspace-governor/tests/test_workspace_governor.py`:

```python
import argparse
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent


def load_module():
    module_path = ROOT / "scripts" / "workspace_governor.py"
    spec = importlib.util.spec_from_file_location("workspace_governor_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run plugin-local tests**

Run:

```bash
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Run full root tests**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugins/documentation-wizard/tests plugins/research-partner/tests plugins/workspace-governor/tests
git commit -m "test: add plugin-local regression entry points"
```

---

### Task 9: Re-Run Plugin Eval And Record Acceptance

**Files:**
- Create or update: `docs/superpowers/plans/2026-06-10-plugin-quality-execution-results.md`

- [ ] **Step 1: Run Plugin Eval for each plugin**

Run:

```bash
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard --format markdown > /tmp/documentation-wizard-plugin-eval.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner --format markdown > /tmp/research-partner-plugin-eval.md
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor --format markdown > /tmp/workspace-governor-plugin-eval.md
```

Expected:

- No `interface-missing-websiteURL` failures.
- No `interface-missing-privacyPolicyURL` failures.
- No `interface-missing-termsOfServiceURL` failures.
- No `description-trigger-weak` warnings.
- Plugin-local test warnings should be reduced or absent.

- [ ] **Step 2: Run all tests and validations**

Run:

```bash
python -m unittest tests/test_plugins_and_agents.py
python - <<'PY'
from pathlib import Path
audit = Path("docs/superpowers/audits/plugin-source-audit.md")
if not audit.exists():
    raise SystemExit("plugin source audit is missing")
text = audit.read_text(encoding="utf-8")
if "Conflict detector passed before implementation continued." not in text:
    raise SystemExit("plugin source audit did not record conflict detector success")
print("plugin source audit recorded")
PY
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-run-smoke
```

Expected: all tests pass; all validates return `"passed": true`; `research-partner run` returns `"status": "ok"` and writes lane JSON files.

- [ ] **Step 3: Write the results note**

Create `docs/superpowers/plans/2026-06-10-plugin-quality-execution-results.md` with this structure:

```markdown
# Plugin Quality Execution Results

## Commands Run

- `python -m unittest tests/test_plugins_and_agents.py`
- `python -m unittest discover -s plugins/documentation-wizard/tests -v`
- `python -m unittest discover -s plugins/research-partner/tests -v`
- `python -m unittest discover -s plugins/workspace-governor/tests -v`
- `python plugins/documentation-wizard/scripts/documentation_wizard.py validate`
- `python plugins/research-partner/scripts/research_partner.py validate`
- `python plugins/workspace-governor/scripts/workspace_governor.py validate`
- `python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-run-smoke`
- `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard --format markdown`
- `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner --format markdown`
- `node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor --format markdown`

## Results

- Root regression suite:
- Plugin-local suites:
- Plugin validations:
- Research Partner lane execution:
- Plugin Eval documentation-wizard:
- Plugin Eval research-partner:
- Plugin Eval workspace-governor:

## Remaining Work

- Token budget reduction:
- Script decomposition:
- Deeper behavioral tests:
```

Replace each bullet value with the actual result from this execution. Do not leave blank values.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-06-10-plugin-quality-execution-results.md
git commit -m "docs: record plugin quality execution results"
```

---

### Task 10: Decide Whether To Refactor Large Scripts

**Files:**
- No required code changes in this task.
- Optional follow-up plan only if Plugin Eval still reports high complexity after the above changes.

- [ ] **Step 1: Inspect Plugin Eval complexity warnings**

Run:

```bash
rg -n "py-complexity-high|deferred_cost_tokens-budget-high|py-long-lines" /tmp/documentation-wizard-plugin-eval.md /tmp/research-partner-plugin-eval.md /tmp/workspace-governor-plugin-eval.md
```

Expected: warnings may remain, especially for `workspace-governor`.

- [ ] **Step 2: Make the decision**

If all three plugins now pass structural checks and the only remaining major warnings are complexity and deferred token cost, stop this implementation branch here. Create a separate plan for script decomposition and token-budget reduction rather than mixing broad refactors into this correctness pass.

Acceptance wording for stopping here:

```text
Structural plugin quality issues are resolved, research-partner executes lanes, and all tests pass. Remaining complexity and budget warnings are deferred to a separate refactor plan because they are not required for functional correctness.
```

- [ ] **Step 3: Commit only if a results note was changed**

```bash
git status --short
git add docs/superpowers/plans/2026-06-10-plugin-quality-execution-results.md
git commit -m "docs: defer script decomposition follow-up"
```

If `git status --short` is clean, do not commit.

---

## Acceptance Gates

The implementation is complete only when all of these pass:

```bash
python -m unittest tests/test_plugins_and_agents.py
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
python plugins/research-partner/scripts/research_partner.py run --repo tests/fixtures/research_repo --output-dir /tmp/research-partner-run-smoke
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze /Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor --format markdown
```

Manual acceptance checks:

- Plugin Eval no longer reports missing interface URL failures for any plugin.
- Plugin Eval no longer reports weak trigger descriptions.
- `docs/superpowers/audits/plugin-source-audit.md` exists and records that conflicting authored plugin definitions were checked before implementation continued.
- `research-partner run` writes `preflight.json`, one JSON file per executable lane, and `bundle.json`.
- Bundled findings preserve lane provenance when multiple lanes report the same title.
- README and skill wording do not claim stronger behavior than the code executes.

## Self-Review

Spec coverage:

- Missing manifest interface URLs: covered by Tasks 1 and 2.
- OpenAI/Codex source repo layout: covered by Tasks 0 and 0.1.
- Conflicting plugin definitions and stale authored installs: covered by Task 0.2.
- Weak trigger descriptions: covered by Tasks 3 and 4.
- `research-partner` actual lane execution: covered by Tasks 5 and 6.
- Provenance risk in bundled lane outputs: covered by Task 7.
- Plugin-local tests for evaluator visibility: covered by Task 8.
- Re-run Plugin Eval and record evidence: covered by Task 9.
- Avoid broad unplanned refactors: covered by Task 10.

Placeholder scan:

- No forbidden placeholder tokens or unspecified edge-case instructions remain.
- Every code-changing task includes exact code or exact replacement text.

Type consistency:

- `run_review(repo_root: Path, output_dir: Path, lanes: list[str] | None = None)` is used consistently by direct tests and CLI dispatch.
- Lane payloads consistently include `scope`, `lane`, `artifact_map`, `findings`, `direct_evidence_vs_inference`, `required_tests_checks`, and `recommended_actions`.
- `bundle_review()` still accepts a preflight path and a list of lane paths.
