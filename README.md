# Codex Personal Plugins

Personal Codex plugins for documentation review, research-analysis review, and workspace organization.

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets generated from this repo.

## Plugins

### Documentation Wizard

`documentation-wizard` audits documentation against the current implementation.

Use it for:

- checking README and `docs/` claims against live CLI flags, schemas, and referenced paths
- finding stale config keys, stale CLI options, and broken documentation links
- flagging maintainer-specific paths that should not appear in public docs
- generating small regression checks for documentation drift

Main helper:

```bash
python plugins/documentation-wizard/scripts/documentation_wizard.py report --repo <path>
```

### Research Partner

`research-partner` runs data-first, methods-aware review lanes for research and analysis repositories.

Use it for:

- reconstructing project-local artifact and path truth before reviewing claims
- checking alignment between code, outputs, documentation, and scientific interpretation
- separating implementation issues from statistical, scientific, and literature-support concerns
- producing a bundled review from deterministic local lanes

Main helper:

```bash
python plugins/research-partner/scripts/research_partner.py run --repo <path> --output-dir <dir>
```

The `run` command writes:

- `preflight.json`
- one JSON file per executable review lane
- `bundle.json`

### Workspace Governor

`workspace-governor` audits workspace layout and publish readiness for local research and analysis projects.

Use it for:

- checking canonical source, runtime, and cloud-output paths
- identifying stale hard-coded path assumptions
- reviewing public/private documentation boundaries
- previewing and verifying safe workspace or publish operations

Main helper:

```bash
python plugins/workspace-governor/scripts/workspace_governor.py assess --repo <path>
```

## Repository Layout

```text
.agents/plugins/marketplace.json      Repo marketplace definition
plugins/documentation-wizard/         Documentation audit plugin
plugins/research-partner/             Research review plugin
plugins/workspace-governor/           Workspace audit plugin
scripts/deploy_plugins.py             Deploy plugins into ~/.codex/plugins
tests/                                Shared regression tests and fixtures
docs/superpowers/                     Plans, audits, and execution notes
```

## Deploy Locally

From the repository root:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

This copies the three plugin directories into `~/.codex/plugins/` and refreshes the personal marketplace metadata under `~/.agents/plugins/marketplace.json`.

## Validate

Run the shared regression suite:

```bash
python -m unittest tests/test_plugins_and_agents.py
```

Run plugin-local suites:

```bash
python -m unittest discover -s plugins/documentation-wizard/tests -v
python -m unittest discover -s plugins/research-partner/tests -v
python -m unittest discover -s plugins/workspace-governor/tests -v
```

Run plugin validators:

```bash
python plugins/documentation-wizard/scripts/documentation_wizard.py validate
python plugins/research-partner/scripts/research_partner.py validate
python plugins/workspace-governor/scripts/workspace_governor.py validate
```

Generate coverage artifacts for Plugin Eval:

```bash
python -m coverage run -m unittest discover
python -m coverage xml
```

Generate per-plugin coverage artifacts for Plugin Eval:

```bash
python scripts/generate_plugin_coverage.py
```

Run the research-partner smoke review:

```bash
python plugins/research-partner/scripts/research_partner.py run \
  --repo tests/fixtures/research_repo \
  --output-dir /tmp/research-partner-run-smoke
```

## Plugin Eval

Run Plugin Eval against each plugin:

```bash
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/documentation-wizard --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/research-partner --format markdown
node /Users/ncamarda/.codex/plugins/cache/openai-curated/plugin-eval/c6ea566d/scripts/plugin-eval.js analyze plugins/workspace-governor --format markdown
```

## Development Notes

- Keep authored source in `plugins/<plugin-name>/`.
- Do not edit installed copies under `~/.codex/plugins/<plugin-name>` directly.
- Keep READMEs focused on current behavior.
- Avoid fallback or temporary rescue logic for failing features; prefer one correct implementation or remove the feature.
- For research and analysis behavior, distinguish descriptive, associational, causal, and predictive/prognostic claims.
