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
