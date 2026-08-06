# Documentation Policy

Use this reference when documentation review requires more detail than the skill entrypoint contains.

## Source-Of-Truth Order

1. parser, schema, or CLI help output
2. generated docs when generation is canonical
3. maintained prose docs such as `README*` and `docs/`

Public docs should remain portable. Maintainer-specific infrastructure belongs in `AGENTS.md` or clearly internal docs such as `.local.md`.

## Helper Commands

- `inventory --repo <path>`
- `interfaces --repo <path>`
- `report --repo <path>`
- `regression-check --repo <path> --kind <cli-flags|config-schema|referenced-paths|private-infra>`
- `sanitize-public-docs --repo <path> [--write]`
- `validate`

`validate` confirms the plugin bundle is registered and its manifest, skill, and assets are present.

## Machine Path Triage

Treat requests to fix machine paths as a diagnosis task first, not as an automatic public-doc rewrite. Start with `report` and `interfaces`, then inspect the cited documentation when path-like examples need context.

Classify each relevant reference as broken in-repo, valid but machine-specific, portable repo-relative, generated-output/example, or unresolved external. Report the document location, direct evidence, user impact, and recommended repair. A missing artifact path or date-stamped output is not automatically a broken link.

Use the following repair order:

1. Use a repo-relative path for a target tracked with the repository.
2. Use a documented environment variable or configuration key for a genuine machine-local or external target.
3. Keep a literal machine path only in `AGENTS.md` or clearly internal operational docs when it remains necessary.

If more than one in-repo target plausibly repairs a broken reference, present the verified candidates and ask the user to choose. Do not guess. Present a concrete replacement preview and receive explicit approval before modifying documentation.

## Public Vs Private Docs

The intended policy is:

- public docs such as `README*` and publish-facing `docs/` should stay portable and should not expose private infrastructure, including:
  - Absolute `/Users/...` paths.
  - Local `Workspaces` source, runtime, results, and archive paths.
  - OneDrive `Project Vault` record paths.
  - Legacy local or synced roots such as `Projects`, `ProjectsRuntime`, `Research`, and `SideProjects`.
- private operational details should live in `AGENTS.md` or clearly internal docs such as `.local.md`
- `sanitize-public-docs` rewrites the public side only; it does not touch `AGENTS.md`
- `sanitize-public-docs` is an explicit approved action, not the default response to a machine-path request

## Limits

- CLI extraction is heuristic and currently optimized for Python `argparse`, Click, and Typer patterns
- config extraction currently targets JSON schema files
- path sanitization uses rule-based rewrites, so the result should still be reviewed by a human
- sanitization should preserve meaningful repo-relative tails such as `output/<file>` or `releases/<date>/` while removing maintainer-specific absolute prefixes
