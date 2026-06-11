---
name: workspace-governor
description: Audits canonical workspace layout, enforces the public/private docs contract, and performs backup-first verified moves plus publish previews.
---

# Purpose

Use this skill when the user wants to audit, clean up, or migrate workspace paths into the canonical layout.

This is a safety-first migration skill, not a blind mover.
It should preserve git history, keep backups until verification passes, and stop on ambiguous classifications rather than guessing.

# Helper script

Use `scripts/workspace_governor.py` as the source of truth:

- `assess --repo <path>`: run the full non-mutating first pass for one repository, bundling repo inspection, workspace planning context, doc-contract checks, rewrite candidates, and publish preview
- `dry-run --repo <path>`: inspect one repository, infer classification inputs, and report unanswered questions plus rewrite candidates
- `audit`: inventory canonical roots, flag ambiguous trees, and build a machine-readable move plan
- `apply --audit <json>`: perform backup-first verified copies and keep rollback paths intact if a move fails
- `verify --manifest <json>`: compare backup and destination state and optionally run a smoke test command
- `publish-preview --repo <path>`: preview publishable runtime artifacts, public-doc rewrites, and the dated cloud snapshot target
- `publish --repo <path> --approve-doc-review`: publish runtime artifacts into the dated cloud snapshot after public-doc review

# Default execution policy

Treat `dry-run`, `audit`, and `publish-preview` as non-mutating steps.
When the user asks for an audit, cleanup, migration review, or publish review, continue through the relevant non-mutating steps in the same turn instead of stopping to ask permission again.

For a first assessment pass, prefer `assess --repo <path>` over manually staging `dry-run`, `audit`, and `publish-preview`.
Do not stop after `dry-run` with a handoff like "If you want, I can run audit next."
Run the full non-mutating assessment before pausing to discuss changes, even when `dry-run` surfaced unresolved questions.
Surface the issues after the assessment pass, then pause before any mutating step.

Pause only when:

- the next step would mutate files or move data, such as `apply` or `publish`
- the user explicitly asked to stop after an earlier step

# Path rewrite behavior

The script reports explicit rewrite candidates during dry-run and audit.
Rewrite planning is separate from file moves so path edits can be reviewed before any mutation.

# Public/private docs policy

- public `README*` and public `docs/` should stay portable and must not expose maintainer-only infrastructure
- `AGENTS.md` is the private operational source of truth
- `analysis_registry.yaml` is the preferred place for structured publish overrides, with `AGENTS.md` as fallback
- publish uses `documentation-wizard` sanitization and pauses for review if public docs were rewritten

# Required workflow

1. Run `assess` for a target repo first.
2. Review the questions, classification, dual-doc contract, rewrite candidates, move plan, and publish-preview findings together.
3. Run `apply` only if the assessment or audit actually contains planned workspace moves.
4. Run `verify` only if `apply` moved anything, then run project-specific smoke tests.
5. Run `publish` only after doc review is complete.

# Safety rules

- Inspect repository-local `AGENTS.md` first, then `analysis_registry.yaml` if present.
- Prefer `analysis_registry.yaml` for structured publish overrides and use `AGENTS.md` as fallback.
- Never move anything before producing an inventory and proposed plan.
- Prefer whole-directory moves for git repositories.
- Do not merge into an existing destination automatically.
- Do not delete the source tree until destination verification passes.
- Keep rewrite planning distinct from file moves.
- Treat "no planned moves" as a valid assessment outcome for repos already in the canonical layout.
- If classification is ambiguous, stop and ask rather than guessing.
