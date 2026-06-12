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

`validate` confirms the plugin bundle is registered and its manifest, skill, and assets are present.

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
