---
name: research-partner
description: Use when a research analysis, manuscript claim, repository, or pipeline needs a data-first multi-lane review grounded in local artifacts.
---

# Purpose

Use this skill when a research analysis, manuscript claim, repository, or pipeline needs a data-first multi-lane review grounded in local artifacts.

Default to `scripts/research_partner.py run --repo <repo> --output-dir <dir>`. Read `references/review-lanes.md` before selecting or interpreting lanes.

# Workflow

Default routing order: `review-preflight`, `documentation-wizard`, specialist lanes, `review-synthesizer`. When path truth is unclear, hand off to `workspace-governor` before specialist review.

1. Reconstruct local artifact and path truth before reviewing methods or claims.
2. Run only the lanes that match the user request.
3. Bundle lane outputs and preserve lane provenance.
4. Separate descriptive, associational, causal, and predictive/prognostic claims.
5. Separate direct evidence, inference, missing evidence, and implementation behavior.
