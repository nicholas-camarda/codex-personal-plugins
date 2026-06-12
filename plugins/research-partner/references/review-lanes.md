# Review Lanes

Use this reference when selecting or interpreting research-partner lanes.

## Default Command

Run `scripts/research_partner.py run --repo <repo> --output-dir <dir>` for end-to-end deterministic local review. Use `inventory` for preflight-only work. Use `bundle` when lane JSON files were produced elsewhere.

## Lanes

- `documentation-wizard`: documentation, methods prose, CLI/config instructions, and file-path promises
- `implementation-auditor`: code path, endpoint definitions, joins, recoding, and output generation
- `stats-reviewer`: estimand or prediction target, method fit, diagnostics, missingness, calibration, discrimination, and validation
- `scientific-reviewer`: claim type, bias, measurement validity, generalizability, and interpretation strength
- `literature-support-reviewer`: whether the actual method and study setting are supported directly or only by analogy
- `robustness-test-designer`: regression, fixture, invariance, perturbation, and smoke tests tied to concrete failure modes

Always separate descriptive, associational, causal, and predictive/prognostic claims. Always distinguish direct evidence, inference, and missing evidence.

## Review Flow Detail

When preflight detects workspace topology risk, it performs a non-mutating `workspace-governor` `dry-run` handoff and folds a small path-review summary into the preflight artifact map. `@research-partner` does not run migrations, applies, or publish steps.

When the repo does not provide strong research-layout evidence, preflight stays conservative: it records a low-confidence generic-repo topology summary instead of sounding certain about `~/Projects`, `~/ProjectsRuntime`, or OneDrive-backed paths.

## Agent Routing

`@research-partner` is an orchestrator, not a single monolithic reviewer. It routes work through these reusable agents:

- `review-preflight`: reconstructs path truth, entrypoints, artifacts, runtime outputs, and missing/stale path assumptions
- `workspace-governor`: supplies a risk-gated dry-run path audit when preflight detects missing declared paths or stale path assumptions
- `documentation-wizard`: checks README, docs, manuscript methods text, CLI/config instructions, and file-path promises
- `implementation-auditor`: traces the concrete code path from inputs to outputs
- `stats-reviewer`: reviews estimands, method fit, assumptions, diagnostics, and validation
- `scientific-reviewer`: reviews claim strength, bias, generalizability, and interpretation inflation
- `literature-support-reviewer`: checks peer-reviewed support versus convention or analogy
- `robustness-test-designer`: turns failure modes into prioritized regression, fixture, invariance, and perturbation tests
- `review-synthesizer`: deduplicates overlapping findings and produces one ranked final review

## Skill To Agent Mapping

- `inspect-analysis-artifacts` -> `review-preflight`
- `review-documentation-consistency` -> `documentation-wizard`
- `review-implementation-validity` -> `implementation-auditor`
- `review-statistical-validity` -> `stats-reviewer`
- `review-scientific-interpretation` -> `scientific-reviewer`
- `assess-literature-support` -> `literature-support-reviewer`
- `design-robustness-tests` -> `robustness-test-designer`
- `synthesize-review` -> `review-synthesizer`

## Default Sequence

1. Run preflight first.
2. Choose only the specialist lanes that match the user's question.
3. Bundle the lane outputs.
4. Finish with synthesis.

Not every review should spawn every specialist lane. Documentation drift may need only preflight plus `documentation-wizard`; method validity may need preflight, `stats-reviewer`, and `scientific-reviewer`.

## Helper Commands

- `inventory --repo <path>`
- `run --repo <path> --output-dir <dir> [--lane <name>]`
- `bundle --preflight <json> --lane <json> [...]`
- `validate`

## Limits

- artifact discovery is heuristic and should be confirmed against project-specific conventions
- generic repos intentionally get a low-confidence topology summary rather than a canonical research workspace guess
- workspace-governor handoff is selective and summarizes only stable path-review fields
- synthesis quality depends on each lane producing the shared output contract
- external literature support still requires real source review when claims depend on it
