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
