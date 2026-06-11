# Assessment of `documentation-wizard`, `research-partner`, and `workspace-governor`

Date: 2026-04-09

## Scope and method

This assessment is non-mutating and grounded in the live plugin workspace under `/Users/ncamarda/.codex/plugins`.

Plugins assessed:
- `documentation-wizard`
- `research-partner`
- `workspace-governor`

Primary evidence reviewed:
- each plugin manifest under `.codex-plugin/plugin.json`
- each plugin `README.md`
- each plugin `SKILL.md`
- helper CLIs in `scripts/*.py`
- shared installer in `scripts/deploy_plugins.py`
- shared tests in `tests/test_plugins_and_agents.py`
- bundled fixtures in `tests/fixtures`

Live commands run:
- `python3 -m unittest tests.test_plugins_and_agents`
- `python3 documentation-wizard/scripts/documentation_wizard.py report --repo tests/fixtures/generic_python_repo`
- `python3 research-partner/scripts/research_partner.py inventory --repo tests/fixtures/minimal_repo`
- `python3 workspace-governor/scripts/workspace_governor.py assess --repo tests/fixtures/research_repo --roots tests/fixtures --snapshot-id smoke-001`
- `python3 workspace-governor/scripts/workspace_governor.py publish-preview --repo tests/fixtures/research_repo --snapshot-id smoke-001`
- `python3 documentation-wizard/scripts/documentation_wizard.py validate`
- `python3 documentation-wizard/scripts/documentation_wizard.py report --repo documentation-wizard`
- `python3 research-partner/scripts/research_partner.py validate`
- `python3 workspace-governor/scripts/workspace_governor.py validate`
- `python3 workspace-governor/scripts/workspace_governor.py dry-run --repo workspace-governor`

Direct evidence takes priority over README or skill claims. Where this report makes an inference, it is labeled as such.

## Executive summary

The three plugins form a coherent local ecosystem, but they are not equally mature.

- `documentation-wizard` is the most concrete as a standalone reviewer: it has a real drift-detection loop, useful JSON output, and self-dogfooding reveals both real value and real correctness issues.
- `research-partner` is mostly an orchestration contract plus a preflight/bundling helper. Its documented multi-lane review system is only partially implemented in code.
- `workspace-governor` has the strongest safety-oriented architecture, but its highest-risk behaviors are under-tested, and some of its classification and publish-preview behavior appears too heuristic for the safety claims it makes.

Across the repo, the current regression suite is real but not yet robust enough to protect the riskiest failure modes. Many tests are smoke-oriented, fixtures are intentionally small and clean, and packaging validation is stronger than behavioral validation.

## Plugin 1: `documentation-wizard`

### Current implemented behavior

The plugin exposes six commands through `documentation_wizard.py`:
- `inventory`
- `interfaces`
- `report`
- `regression-check`
- `sanitize-public-docs`
- `validate`

The actual flow is:
1. Inventory documentation surfaces, public-doc surfaces, and likely source-of-truth files.
2. Extract CLI flags from Python source using regexes for `argparse`, Click, and Typer.
3. Extract config keys from JSON schema files.
4. Extract documented flags and backticked config-like identifiers from public docs.
5. Compare documented versus extracted surfaces and emit JSON findings.
6. Detect private infrastructure mentions and optionally rewrite them in public docs.

Observed fixture behavior:
- On `tests/fixtures/generic_python_repo`, `report` returned a clean audit with no stale CLI flag or stale config key findings.
- On the plugin itself, `report --repo documentation-wizard` returned five findings:
  - broken reference to `scripts/deploy_plugins.py`
  - broken reference to `.local.md`
  - private infra leak for `OneDrive`
  - private infra leak for `~/ProjectsRuntime`
  - private infra leak for `/Users/...`

Observed validation behavior:
- `validate` passed, but all checks were packaging/registration/documentation-presence checks.
- It did not detect the README drift found by the plugin’s own `report`.

### Claimed versus actual behavior

Implemented:
- heuristic documentation inventory
- heuristic Python CLI extraction
- JSON-schema config extraction
- referenced-path checks from documentation text
- private-infrastructure leak detection and rewrite preview

Claimed more broadly than implemented:
- README and skill describe “help output” as source-of-truth, but the script does not run CLI help.
- README says it extracts “referenced file paths from code,” but current referenced-path checks are driven from docs, not code.
- Skill language suggests a stronger source-of-truth model than the current heuristics actually provide.

### Strengths

- Simple, transparent implementation.
- JSON findings include severity, impact, and patch direction, which makes the tool actionable.
- The public/private docs policy is consistently expressed in manifest-facing docs and script behavior.
- Self-dogfooding surfaces real drift instead of only passing happy-path fixtures.

### Missing capabilities

- No runtime help extraction.
- No non-Python CLI support.
- No richer config-surface extraction beyond `*.schema.json`.
- No explicit schema or version contract for report payloads.
- No built-in mechanism to distinguish likely false positives from high-confidence findings.

### Risks and ambiguities

- False confidence risk: `validate` passes even when the plugin’s own public docs drift from reality.
- Sanitizer quality risk: self-report suggested replacing `OneDrive` with `OneDrive` and `/Users/...` with `Users/...`, which is not a meaningful sanitization improvement.
- Detection noise risk: the path-matching logic is broad enough to overmatch illustrative text.
- Portability risk: validation assumes a very specific home-install model.

### Test coverage assessment

What is actually covered:
- public-doc file pruning behavior
- Click and Typer flag extraction
- generic fixture smoke report
- installed-plugin smoke execution through the home plugin workspace

What is only smoke-tested:
- end-to-end report correctness on realistic docs
- sanitizer correctness
- regression-check correctness
- false-positive path detection
- mismatch between README/skill claims and extractor behavior

High-risk gaps in tests:
- no adversarial sanitizer tests
- no tests for noisy or ambiguous path tokens
- no tests that `validate` should fail when README claims are stale
- no tests for non-JSON-schema config surfaces or dynamic CLI definitions

### Prioritized improvements

1. Add fixture-based tests for sanitizer correctness, false positives, and drift findings on intentionally messy docs.
2. Fix `portable_public_replacement()` and related path-rewrite behavior so replacements are genuinely portable.
3. Either implement help-output extraction or narrow the README and skill contract to match the current script.
4. Expand config and CLI extraction beyond the current Python/JSON-schema heuristics.
5. Add stable output shaping for CI, including summary counts and clearer failure modes.

## Plugin 2: `research-partner`

### Current implemented behavior

The plugin exposes three commands through `research_partner.py`:
- `inventory`
- `bundle`
- `validate`

The actual flow is narrower than the top-level plugin description suggests:
1. `inventory` walks a repo and records `AGENTS.md`, `analysis_registry.yaml`, scripts, tests, notebooks, and simple data-like directory names.
2. It heuristically classifies workspace topology and may call `workspace-governor dry-run` when evidence suggests a research-layout repo.
3. It emits a JSON preflight payload with findings, recommended actions, and a default flow list.
4. `bundle` merges preflight and lane JSON files, deduplicating findings by title/message and keeping the higher-severity version.
5. `validate` checks local installation and presence of required skills and peer-plugin dependencies.

Observed fixture behavior:
- `inventory --repo tests/fixtures/minimal_repo` produced a conservative preflight report with generic topology, no findings, and a recommended action to proceed to specialist review lanes.
- On the generic fixture, topology remained intentionally low-confidence, which matches the conservative design.

Observed validation behavior:
- `validate` passed and confirmed required skills plus the presence of documentation-wizard and workspace-governor peer dependencies.
- As with the other plugins, these checks prove installation shape more than runtime review correctness.

### Claimed versus actual behavior

Implemented:
- preflight inventory
- heuristic workspace topology classification
- optional non-mutating handoff to workspace-governor
- lane-output bundling
- installation validation

Claimed more broadly than implemented:
- README and skills describe a multi-lane orchestrator routing work through documentation, implementation, stats, scientific interpretation, literature, robustness, and synthesis reviewers.
- The current script does not run those lanes. It only inventories and bundles externally produced outputs.
- Skill text implies deeper artifact reconstruction than the current tree walk actually performs.

### Strengths

- Conservative topology handling is a good design choice.
- Clear separation between preflight and bundle phases.
- Dependency discovery for peer plugins is more portable than hard-coded sibling-only assumptions.
- The plugin is explicit that documentation-wizard and workspace-governor are reusable lanes rather than hidden magic.

### Missing capabilities

- No actual lane execution orchestration.
- No schema validation for lane outputs before bundling.
- No explicit provenance preservation when findings from multiple lanes overlap.
- No deep artifact reconstruction of actual analysis inputs, runtime outputs, or published outputs.
- No machine-enforced shared lane contract across the skill set.

### Risks and ambiguities

- Biggest gap: the README presents a stronger orchestration system than the helper CLI currently implements.
- Deduplicating bundle findings by title/message risks collapsing meaningful disagreements across lanes.
- Windows path hints are partially recognized but not fully handled.
- Manifest capability includes `Write`, but the current operational boundary is mostly analysis and bundling.
- Validation depends on peer-plugin presence, but there is little direct behavior testing for failure or partial-install states.

### Test coverage assessment

What is actually covered:
- peer-plugin root resolution
- declared-path parsing in prose
- blocking behavior when workspace-governor handoff returns open questions
- minimal fixture inventory smoke behavior
- generic repo topology staying low-confidence
- installed-plugin smoke execution

What is only smoke-tested:
- whether bundled outputs preserve the right evidence and nuance
- whether the documented lane system actually behaves as advertised
- whether malformed lane payloads are rejected or mis-merged

High-risk gaps in tests:
- no tests for malformed lane JSON
- no tests for provenance-preserving bundle behavior
- no tests for conflicting findings across lanes
- no tests for missing or broken workspace-governor handoff
- no tests for stronger artifact reconstruction behavior promised by skills

### Prioritized improvements

1. Implement a real lane runner or narrow the plugin contract to preflight-plus-bundle.
2. Define and enforce one JSON schema for lane outputs.
3. Preserve lane provenance when bundling overlapping findings.
4. Expand preflight from repo-shape inventory to actual artifact reconstruction.
5. Add negative tests for malformed inputs, conflicting lanes, and missing peer plugins.

## Plugin 3: `workspace-governor`

### Current implemented behavior

The plugin exposes eight commands through `workspace_governor.py`:
- `assess`
- `dry-run`
- `audit`
- `apply`
- `verify`
- `publish-preview`
- `publish`
- `validate`

The intended flow is actually present in code:
1. `dry-run` inspects one repo, infers project profile, proposes code/runtime/cloud homes, evaluates doc-contract requirements, and lists rewrite candidates and open questions.
2. `audit` scans workspace roots and builds a machine-readable move plan.
3. `assess` combines `dry-run`, `audit`, and publish-preview style information into one JSON payload.
4. `apply` performs backup-first migration work with copy-to-backup, copy-to-temp, signature checks, git checks, rename, and cleanup.
5. `verify` re-checks move results and can run an optional smoke command.
6. `publish-preview` and `publish` use documentation-wizard, infer runtime/cloud targets, enumerate publishable candidates, and protect against destination collisions.

Observed fixture behavior:
- `assess --repo tests/fixtures/research_repo --roots tests/fixtures --snapshot-id smoke-001` returned a detailed structured payload with a research profile, no move plan, one unresolved smoke-test question, and no publishable runtime artifacts because the fixture has no runtime tree.
- `publish-preview` on the research fixture returned no publishable artifacts and no doc-rewrite requirement.
- `dry-run --repo workspace-governor` classified the plugin itself as `general` with low confidence and treated the dual-doc contract as advisory.

Observed validation behavior:
- `validate` passed, but checks are still mainly packaging, asset, marketplace, and README/skill-presence checks.

### Claimed versus actual behavior

Implemented:
- real non-mutating assessment flow
- safety-oriented apply/verify workflow
- publish-preview and publish mechanics
- documentation-wizard integration for doc policy

Claimed more strongly than current evidence supports:
- README and skill position this as a safe migration and publish system, but the highest-risk behaviors are not robustly covered by tests.
- README language around rewrite planning and canonical enforcement is broader than the rewrite-candidate logic currently used.

### Strengths

- Strongest concrete architecture of the three plugins.
- Safety-first apply flow is credible by inspection.
- Metadata override handling via `analysis_registry.yaml` plus `AGENTS.md` fallback is well thought through.
- Publish collision checks happen before copy.
- Documentation policy is integrated rather than bolted on.

### Missing capabilities

- No restore command from backups after apply.
- No schema versioning for generated JSON manifests or reports.
- Rewrite detection is narrower than the overall publish/doc policy framing suggests.
- No graceful degradation if documentation-wizard is missing or broken.
- Limited classification awareness for plugin repos and other non-research but non-generic special cases.

### Risks and ambiguities

- Safety-critical paths are more inspected than behaviorally proven.
- The plugin hard-depends on documentation-wizard for parts of `assess` and publish flows.
- The default assessment scope may be broader and slower than necessary for one-repo review.
- The repo’s own `dry-run` output shows how easily classification falls back to a weakly evidenced general profile.
- There is evidence from prior analysis and code inspection that publish candidate filtering should be treated as a high-risk area even though the clean fixture does not stress it.

### Test coverage assessment

What is actually covered:
- fallback peer-plugin root resolution
- publish failure when a destination already exists
- research fixture assess smoke behavior
- general project type metadata handling
- installed-plugin smoke execution

What is only smoke-tested:
- `apply`
- `verify`
- publish candidate filtering quality
- backup integrity and rollback correctness
- classification conflicts and precedence
- dependency failure when documentation-wizard is unavailable

High-risk gaps in tests:
- no tests for `apply` rollback and recovery behavior
- no tests for `verify` with real manifests from move operations
- no tests for publish-preview overinclusive file sets
- no tests for classification conflicts such as legacy git repo plus research metadata
- no tests for missing or failing documentation-wizard dependency

### Prioritized improvements

1. Add behavior tests for `apply`, `verify`, rollback, and backup recovery.
2. Add classification-conflict tests and explicitly lock precedence rules.
3. Add publish-preview tests on messy runtime trees with backups, `.git_*`, and borderline artifacts.
4. Add dependency-failure tests when documentation-wizard is missing or errors.
5. Consider reducing the default assessment blast radius or making workspace-wide audit more explicitly opt-in.

## Cross-plugin synthesis

### Dependency graph and operational coupling

The three plugins are not independent:
- `research-partner` depends conceptually on both `documentation-wizard` and `workspace-governor`.
- `workspace-governor` directly calls `documentation-wizard` for doc policy checks.
- `scripts/deploy_plugins.py` is the shared installer/marketplace writer and validation orchestrator for all three.

This creates a useful local ecosystem, but it also means:
- a weak validator in one plugin can mask drift that affects another
- missing peer plugins can break flows outside the plugin where the failure originated
- cross-plugin contract drift is currently easier to create than to detect

### Shared validation model

The strongest current validation story is installation hygiene:
- manifest names
- display names
- marketplace registration
- asset presence
- skill presence
- some README/skill mention checks

The weakest current validation story is runtime correctness:
- validators do not generally assert the plugin’s own docs are true
- validators do not exercise the riskiest operational paths
- validators do not enforce stable JSON schemas across helpers

### Shared documentation drift

At least two plugins show evidence that their public docs drift from live behavior:
- `documentation-wizard` self-report found broken references and weak sanitizer suggestions in its own README.
- `workspace-governor` validation can pass despite similar README-level drift risk.
- `research-partner` has a subtler form of drift: its top-level description describes a richer orchestration system than the CLI actually implements.

### Shared testing weaknesses

The test suite is valuable but currently skewed toward:
- installation checks
- happy-path smoke tests
- a handful of targeted unit behaviors

It is weak on:
- adversarial inputs
- messy real-world fixtures
- contract-drift detection
- negative dependency scenarios
- safety-critical mutation paths
- stable output/schema guarantees

## Critical audit of the current test suite

### Current test categories

Install and packaging checks:
- plugin installation into a staged home workspace
- marketplace generation
- plugin `validate` execution after install
- peer-plugin path resolution

Behavioral assertions:
- declared-path parsing in prose
- blocking specialist review when workspace handoff has open questions
- publish failure when destination exists
- iter-files pruning of non-public directories
- general project type metadata handling
- Click and Typer flag extraction

Smoke tests:
- documentation-wizard report on generic fixture
- research-partner inventory on minimal fixture
- workspace-governor assess on research fixture
- installed plugin executions for all three plugins

Missing high-risk scenarios:
- sanitizer correctness and non-destructive replacements
- malformed lane payloads and merge conflicts
- provenance-preserving bundling
- classification conflicts and precedence
- apply/verify rollback behavior
- publish-preview overinclusive candidate selection
- missing peer plugin scripts
- partial installation states
- contract drift between README, skill, manifest, and script

### Are the fixtures realistic enough?

No, not for the riskiest behaviors.

The current fixtures are intentionally small and clean:
- `generic_python_repo` is a tidy argparse plus JSON-schema repo with matching docs.
- `minimal_repo` is almost empty.
- `research_repo` is a minimal metadata-driven research-shaped repo.

These are useful sanity fixtures, but they understate:
- ambiguity
- messy docs
- stale paths
- runtime artifact sprawl
- multiple competing metadata signals
- path-rewrite edge cases
- publish denylist problems

Inference: the current fixture design is better at proving commands work on friendly inputs than at catching the silent bad behavior most likely to hurt users.

### Would the current tests catch contract drift?

Only partially.

They would catch:
- missing skills
- broken installer expectations
- some peer-plugin resolution failures
- a few smoke-level command regressions

They would not reliably catch:
- README promises exceeding implementation
- validators that pass while docs drift
- research-partner overclaiming orchestration capabilities
- weak or malformed sanitization replacements
- unstable JSON shapes so long as top-level smoke assertions still pass

### Would the current tests catch safety-critical failures?

Not well enough.

Most safety-critical `workspace-governor` behavior is not exercised in realistic scenarios. The suite checks one destination-exists failure case, but not the harder failure modes:
- rollback
- restore from backup
- verify behavior on real move manifests
- messy publish-preview candidate sets
- dependency failure inside assess/publish flows

## Prioritized improvement backlog

### Highest priority

1. Add robust tests for `workspace-governor` mutation safety paths.
2. Add adversarial and noisy fixtures for `documentation-wizard`.
3. Add schema and provenance tests for `research-partner` lane bundling.
4. Add explicit tests for cross-plugin dependency failure and partial installation.
5. Add tests that compare README/skill claims against live helper behavior for all three plugins.

### Medium priority

1. Introduce stable JSON schema/version checks for helper outputs.
2. Expand fixtures from clean smoke repos to messy, realistic repos.
3. Strengthen validators so they detect meaningful contract drift, not just packaging correctness.
4. Narrow or clarify plugin README claims where implementation is intentionally heuristic.

### Lower priority but still useful

1. Add summary assertions and deterministic ordering checks for JSON output.
2. Add more platform-path edge cases, especially Windows-like paths and mixed environments.
3. Add tests for larger doc inventories and more varied config/CLI patterns.

## Bottom line

The plugin ecosystem is promising and already useful, but it currently relies too much on clean fixtures, packaging validation, and human interpretation.

The biggest practical risk is not that the plugins do nothing. It is that they appear more verified and more behaviorally complete than they actually are. That gap shows up in three forms:
- validators passing while docs drift
- README/skill contracts outrunning implementation
- tests proving happy-path execution more than high-risk correctness

The next wave of work should prioritize tests that catch silent bad behavior over new surface area. In particular:
- make `documentation-wizard` prove its sanitizer and drift detector on adversarial fixtures
- make `research-partner` prove its bundle semantics and contract boundaries
- make `workspace-governor` prove its safety claims under failure, conflict, and messy publish conditions
