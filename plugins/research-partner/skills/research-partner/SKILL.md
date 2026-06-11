---
name: research-partner
description: Use when a research analysis, manuscript claim, repository, or pipeline needs a data-first multi-lane review grounded in local artifacts.
---

# Purpose

Use this skill to review one analysis, a manuscript-facing claim, a set of scripts, or an entire repository.

Default to `scripts/research_partner.py run --repo <repo> --output-dir <dir>` for end-to-end review execution. Use `inventory` only when the user explicitly wants preflight without lane execution, and use `bundle` only when lane JSON files were produced elsewhere.

This skill acts as a skeptical research partner.
It should reason from the actual project data and implementation first, then add methodological and literature support.

# Default workflow

Default routing order:
- `review-preflight`
- `documentation-wizard` when docs, methods prose, or interface promises matter
- the smallest matching specialist lane set
- `review-synthesizer`

When preflight finds missing declared paths, noncanonical roots, or stale path assumptions, it should run a non-mutating `workspace-governor` dry-run handoff before specialist review relies on those paths.

## Phase 1: Scope the request
Determine whether the task is:
- one-off analysis review
- manuscript/result review
- method-justification review
- implementation audit
- robustness test design
- repo-wide audit

Identify:
- target scripts/functions/notebooks
- target outputs/tables/figures
- claimed scientific question
- claimed estimand or prediction target

## Phase 2: Discover project artifact locations
Check the repository AGENTS.md first, then analysis_registry.yaml if present.

By default, expect a split architecture such as:
- source repo under ~/Projects/<slug>
- runtime/intermediate artifacts under ~/ProjectsRuntime/<slug>
- original input data and published/final outputs stored under ~/Library/CloudStorage/OneDrive-Personal/.../<slug>/<date>/

Do not guess canonical paths if the project defines them.
If paths are inconsistent across code and docs, flag that explicitly.

## Phase 3: Reconstruct what the analysis actually does
Inspect:
- actual data objects used by the target analysis
- runtime artifacts and cached intermediates
- published outputs or final tables if present
- code path from input to final result
- project tests and fixtures
- methods documentation and manuscript text if present

Before giving any methodological opinion, answer:
- what data entered the analysis
- how the outcome was defined
- how time origin and censoring were defined if relevant
- what exclusions occurred
- what exact output was produced

## Phase 4: Parallel review lanes
Use these lanes as needed:
- stats-reviewer
- scientific-reviewer
- implementation-auditor
- robustness-test-designer
- literature-support-reviewer
- documentation-wizard when documentation or manuscript-facing claims are part of scope

## Phase 5: Synthesize
Combine findings into:
1. Scope
2. Bottom line
3. Statistical critique
4. Scientific critique
5. Implementation audit
6. Failure modes and edge cases
7. Required tests
8. Literature/practical support
9. Recommended actions

# Non-negotiable rules

- Use actual project data and outputs first.
- Do not give generic methodological advice before inspecting concrete artifacts.
- Do not assume code matches the writeup.
- Do not confuse discrimination with calibration.
- Do not confuse causal, associational, descriptive, and predictive claims.
- Tie major concerns to concrete implications and tests.
- State uncertainty explicitly.

# Repo-wide review behavior

When asked to review an entire repository:
- identify all major analyses
- identify shared helper functions that propagate risk across analyses
- look for repeated methodological or implementation patterns
- recommend common test infrastructure and analysis registries
