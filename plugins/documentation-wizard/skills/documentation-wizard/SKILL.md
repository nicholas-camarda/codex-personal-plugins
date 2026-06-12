---
name: documentation-wizard
description: Use when documentation must be checked against the current code, CLI flags, schemas, paths, or public/private documentation contract.
---

# Purpose

Use this skill when documentation must be checked against current code, CLI flags, config schemas, paths, or public/private documentation boundaries.

For detailed source-of-truth ordering and helper commands, read `references/documentation-policy.md`.

# Default Workflow

1. Run `scripts/documentation_wizard.py report --repo <path>` for evidence-backed drift review.
2. Use `interfaces` when the user asks specifically about CLI flags, config keys, or referenced paths.
3. Use `sanitize-public-docs --repo <path>` to preview public-doc path cleanup.
4. Use `sanitize-public-docs --repo <path> --write` only after the user approves edits.

# Output Expectations

Return concrete findings with source references, user impact, direct evidence versus inference, and the smallest correction that resolves the drift.
