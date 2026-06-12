---
name: workspace-governor
description: Use when workspace paths, canonical research layout, public/private docs, migration plans, or publish previews need audit or verification.
---

# Purpose

Use this skill when workspace paths, canonical research layout, public/private docs, migration plans, or publish previews need audit or verification.

For canonical layout, safe-flow, and publish-flow details, read `references/workspace-policy.md`.

# Default Workflow

1. Prefer `assess --repo <path>` for a first non-mutating pass via `scripts/workspace_governor.py`.
2. Run the full non-mutating assessment before pausing to discuss changes.
3. Surface classification, doc-contract, rewrite, move-plan, and publish-preview issues together.
4. Pause before mutating commands such as `apply` or `publish`.
5. Use `verify --manifest <json>` after any approved apply.

# Output Expectations

Report concrete path evidence, unresolved questions, publish risks, and verification steps. Do not merge destinations or silently rewrite files.
