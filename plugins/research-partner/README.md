# Research Partner

`@research-partner` is a local Codex plugin for data-first review of analysis repositories.

## Using it in Codex

Invoke it directly in the composer with `@research-partner`, then describe the review you want.

## Review flow

1. `review-preflight` reconstructs artifact and path truth.
2. Selected specialist lanes review documentation consistency, implementation, statistics, scientific interpretation, literature support, and robustness.
3. `review-synthesizer` merges the lane outputs into one ranked review.

When preflight detects workspace topology risk, it performs a non-mutating `workspace-governor` `dry-run` handoff and folds a small path-review summary into the preflight artifact map. `@research-partner` does not run migrations, applies, or publish steps.

When the repo does not provide strong research-layout evidence, preflight stays conservative: it records a low-confidence generic-repo topology summary instead of sounding certain about `~/Projects`, `~/ProjectsRuntime`, or OneDrive-backed paths. Strong path assumptions are only surfaced when repository metadata and local evidence support them.

## Agent routing

`@research-partner` is an orchestrator, not a single monolithic reviewer. It is intended to route work through these explicit reusable agents:

- `review-preflight`: reconstructs path truth, entrypoints, artifacts, runtime outputs, and missing/stale path assumptions before any specialist review starts
- `workspace-governor`: supplies a risk-gated dry-run path audit when preflight detects missing declared paths, noncanonical roots, or stale path assumptions
- `documentation-wizard`: checks whether README, docs, manuscript methods text, CLI/config instructions, and file-path promises match the live code and schema surface
- `implementation-auditor`: traces the concrete code path from inputs to outputs and checks whether the implemented analysis matches the claimed one
- `stats-reviewer`: reviews estimands or prediction targets, method fit, assumptions, diagnostics, validation, and related statistical failure modes
- `scientific-reviewer`: reviews claim strength, bias, generalizability, measurement/design alignment, and interpretation inflation
- `literature-support-reviewer`: checks how well the actual method and study setting are supported by peer-reviewed literature versus convention or analogy
- `robustness-test-designer`: turns concrete failure modes discovered in other lanes into prioritized regression, fixture, invariance, and perturbation tests
- `review-synthesizer`: deduplicates overlapping findings across lanes and produces one ranked, actionable final review

## Skill to agent mapping

The plugin also exposes lane-specific skills that correspond to the reusable agents above:

- `inspect-analysis-artifacts` -> `review-preflight`
- `review-documentation-consistency` -> `documentation-wizard`
- `review-implementation-validity` -> `implementation-auditor`
- `review-statistical-validity` -> `stats-reviewer`
- `review-scientific-interpretation` -> `scientific-reviewer`
- `assess-literature-support` -> `literature-support-reviewer`
- `design-robustness-tests` -> `robustness-test-designer`
- `synthesize-review` -> `review-synthesizer`

## Default sequence

The intended default sequence is:

1. Run preflight first.
2. Choose only the specialist lanes that match the user’s question.
3. Bundle the lane outputs.
4. Finish with synthesis.

Preflight may selectively call `workspace-governor dry-run` when path evidence is weak. That handoff is for path truth only and should stay non-mutating.

Not every review should spawn every specialist lane. For example:

- documentation or methods-writeup drift concerns may need `review-preflight` plus `documentation-wizard`
- implementation-only concerns may need `review-preflight` plus `implementation-auditor`
- method validity questions may need `review-preflight`, `stats-reviewer`, and `scientific-reviewer`
- claim-support questions may additionally need `literature-support-reviewer`
- once concrete failure modes exist, `robustness-test-designer` becomes useful

## What Is Not In Scope

The documentation lane inside `@research-partner` is backed by the reusable `documentation-wizard` reviewer. That means documentation review is now part of the available lane stack, but it still should be selected intentionally when doc/manuscript/methods alignment matters.

Similarly, `@research-partner` does not imply that every lane always runs automatically. The plugin is meant to make the routing explicit and selective rather than silently spinning up unrelated reviewers.

## Helper script

Run `scripts/research_partner.py` with one of:

- `inventory --repo <path>`
- `run --repo <path> --output-dir <dir> [--lane <name>]`
- `bundle --preflight <json> --lane <json> [...]`
- `validate`

`validate` confirms the plugin bundle is registered and its manifest, skills, dependencies, and assets are present.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

From the repository root, run:

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```

The deploy script copies this plugin into `~/.codex/plugins/research-partner` and refreshes the personal marketplace at `~/.agents/plugins/marketplace.json`.

## Limits

- artifact discovery is heuristic and should be confirmed against project-specific conventions
- generic repos intentionally get a low-confidence topology summary rather than a canonical research workspace guess
- workspace-governor handoff is selective and summarizes only stable path-review fields rather than exposing the full dry-run payload
- synthesis quality depends on each lane producing the shared output contract
- external literature support still requires real source review when claims depend on it
