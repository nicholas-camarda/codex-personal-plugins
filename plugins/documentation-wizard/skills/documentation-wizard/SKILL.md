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
3. For requests to fix, clean up, or explain machine paths, follow **Machine-path triage** instead of starting sanitization.
4. Use `sanitize-public-docs --repo <path>` only to produce an approved rewrite preview.
5. Use `sanitize-public-docs --repo <path> --write` only after the user approves the concrete edits.

## Machine-path triage

When a user asks for help with machine paths, local paths, non-portable paths, or broken documentation paths:

1. Start read-only. Run `report` and `interfaces`, then inspect the cited documentation references as needed. Cover ordinary documentation links and path-like examples, not only the known private-infrastructure patterns.
2. Classify every relevant reference as one of:
   - **Broken in-repo**: a tracked relative target is missing.
   - **Valid but machine-specific**: an absolute or user-specific local path works only on one machine.
   - **Portable repo-relative**: a path is already suitable for collaborators and needs no change.
   - **Generated-output/example**: a result, artifact, date-stamped output, or illustrative path is not expected to exist in a fresh checkout.
   - **Unresolved external**: the target is outside the repository and cannot be verified from the checked-out project.
3. Return a compact repair plan for each actionable reference with its exact document location, evidence, user impact, and recommended change. Do not claim an external target exists when it cannot be verified.
4. Use this default repair policy:
   - Prefer a repo-relative reference when the target is tracked with the repository.
   - Recommend a documented environment variable or configuration key for genuine machine-local or external locations.
   - Keep literal machine paths only in `AGENTS.md` or clearly internal operational documentation when they are still necessary.
   - For multiple verified in-repo candidates, show the candidates and ask the user to choose; never guess.
5. End with a concise approval checkpoint before editing. Offer an exact replacement preview, then use `sanitize-public-docs --write` or targeted documentation edits only after explicit approval.

Do not automatically sanitize, rewrite, or apply a generic replacement merely because a path is absolute. The triage must distinguish a broken path from a valid non-portable instruction and from a generated-output example.

# Output Expectations

Return concrete findings with source references, user impact, direct evidence versus inference, and the smallest correction that resolves the drift.
