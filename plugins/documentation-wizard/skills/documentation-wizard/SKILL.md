---
name: documentation-wizard
description: Inventories documentation surfaces, extracts the real interface surface from code and schemas, and reports evidence-backed documentation drift.
---

# Purpose

Use this skill when you need to verify that documentation matches the current codebase and user-facing behavior.

This skill maps directly to the reusable `documentation-wizard` agent and its shared review contract:
- `Scope`
- `Artifact map / evidence reviewed`
- `Findings`
- `Direct evidence vs inference`
- `Required tests / checks`
- `Recommended actions`

# Source-of-truth precedence

Use this precedence order whenever documentation disagrees with implementation:
1. parser, schema, or CLI help output
2. generated docs when generation is canonical
3. maintained prose docs such as `README*` and `docs/`

Do not let copied prose override a parser or schema.

Public/private docs rule:
- public docs should stay portable and must not expose maintainer-only infrastructure such as `OneDrive`, `~/ProjectsRuntime`, or `/Users/...`
- concrete local/cloud topology belongs in `AGENTS.md` or clearly internal docs such as `.local.md`

# Helper script

Use `scripts/documentation_wizard.py` to ground the review:

- `inventory --repo <path>`: enumerate doc surfaces and likely source-of-truth files
- `interfaces --repo <path>`: extract CLI flags, config schema keys, and referenced paths
- `report --repo <path>`: produce a drift report with severity, impact, and patch direction
- `regression-check --repo <path> --kind <cli-flags|config-schema|referenced-paths|private-infra>`: generate a lightweight regression check
- `sanitize-public-docs --repo <path> [--write]`: rewrite public docs to remove maintainer-specific infrastructure details while leaving `AGENTS.md` and internal docs untouched

# Required workflow

1. Inventory the doc surfaces that users actually read.
2. Extract the live interface surface from code, schemas, and help output when feasible.
3. Compare docs to live interfaces and file-path promises.
4. For each mismatch or public-doc infrastructure leak, report:
   - the doc location
   - the source-of-truth reference
   - severity
   - concrete user impact
   - the smallest correct patch direction
5. When public docs leak maintainer-only paths, prefer moving the concrete path into `AGENTS.md` and rewriting the public text into generic, portable language.
   Preserve meaningful relative path context when possible, such as `output/<file>` or `releases/<date>/`, instead of flattening everything into a generic label.
6. Propose one lightweight regression check for the highest-risk drift class.

# Guardrails

- Prefer reproducible inspection over guesswork.
- If you cannot verify a claim, mark it as inferred or missing.
- Do not rewrite large sections of docs when a minimal correction is enough.
