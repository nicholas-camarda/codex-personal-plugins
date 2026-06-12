# Documentation Wizard

`@documentation-wizard` is a local Codex plugin for evidence-backed documentation audits.

## Using it in Codex

Invoke it directly in the composer with `@documentation-wizard`, then describe the repo or drift check you want.

## What it does

- inventories documentation surfaces such as `README*`, `docs/`, and help output
- extracts CLI flags from common Python CLI surfaces, config schema keys, and referenced file paths from code
- reports documentation drift with severity, user impact, and source-of-truth references
- flags maintainer-only infrastructure details when they leak into public docs
- offers a sanitization step that rewrites public docs while leaving `AGENTS.md` and internal docs as the place for concrete local/cloud paths
- generates lightweight regression checks for common drift classes

## Helper script

Run `scripts/documentation_wizard.py` with one of:

- `inventory --repo <path>`
- `interfaces --repo <path>`
- `report --repo <path>`
- `regression-check --repo <path> --kind <cli-flags|config-schema|referenced-paths|private-infra>`
- `sanitize-public-docs --repo <path> [--write]`
- `validate`

`validate` confirms the plugin bundle is registered and its manifest, skill, and assets are present.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

From the repository root, run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

The deploy script copies this plugin into `~/.codex/plugins/documentation-wizard` and refreshes the personal marketplace at `~/.agents/plugins/marketplace.json`.

## Public Vs Private Docs

The intended policy is:

- public docs such as `README*` and publish-facing `docs/` should stay portable and should not expose maintainer-specific paths like `OneDrive`, `~/ProjectsRuntime`, or `/Users/...`
- private operational details should live in `AGENTS.md` or clearly internal docs such as `.local.md`
- `sanitize-public-docs` rewrites the public side only; it does not touch `AGENTS.md`

## Limits

- CLI extraction is heuristic and currently optimized for Python `argparse`, Click, and Typer patterns
- config extraction currently targets JSON schema files
- path sanitization uses rule-based rewrites, so the result should still be reviewed by a human
- sanitization should preserve meaningful repo-relative tails such as `output/<file>` or `releases/<date>/` while removing maintainer-specific absolute prefixes
