---
name: review-documentation-consistency
description: Reviews whether manuscript, README, methods prose, and operational docs match the live code, schema, and file-path surface.
---

Use this skill for the `documentation-wizard` lane inside `@research-partner`.

Ground the review with the installed sibling `documentation-wizard` helper script that ships with the plugin bundle. Do not hard-code a repo-relative path for that helper because the lane should work from source checkouts, personal installs, and cached plugin copies.

Recommended commands:
- run the sibling `documentation_wizard.py inventory --repo <path>` helper
- run the sibling `documentation_wizard.py interfaces --repo <path>` helper
- run the sibling `documentation_wizard.py report --repo <path>` helper

Required output contract:
- `Scope`
- `Artifact map / evidence reviewed`
- `Findings`
- `Direct evidence vs inference`
- `Required tests / checks`
- `Recommended actions`

Focus on:
- README, docs, manuscript methods text, and runbook claims that users or reviewers will actually rely on
- CLI flags, config keys, file paths, and workflow steps that may have drifted from the live implementation
- the smallest documentation correction that resolves the mismatch

Prefer source-of-truth precedence in this order:
1. parser, schema, or generated help output
2. generated docs when generation is canonical
3. maintained prose docs such as `README*`, `docs/`, and manuscript text

Do not let copied prose override the implementation.
