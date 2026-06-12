# Documentation Wizard

`@documentation-wizard` is a local Codex plugin for evidence-backed documentation audits.

## Using it in Codex

Invoke it directly in the composer with `@documentation-wizard`, then describe the repo or drift check you want.

## What it does

- inventories documentation surfaces such as `README*`, `docs/`, and help output
- extracts CLI flags from Python CLI surfaces, config schema keys, and referenced paths
- reports documentation drift with severity and source-of-truth references
- flags maintainer-only infrastructure leaking into public docs
- offers sanitization that rewrites public docs while preserving `AGENTS.md` path truth

## Helper script

```bash
python plugins/documentation-wizard/scripts/documentation_wizard.py report --repo <path>
```

See `references/documentation-policy.md` for all commands, public/private doc policy, and limits.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```
