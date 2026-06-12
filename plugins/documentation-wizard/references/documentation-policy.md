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
