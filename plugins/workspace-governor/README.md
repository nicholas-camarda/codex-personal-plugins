# Workspace Governor

`@workspace-governor` is a local Codex plugin for safe workspace migration and publish-gated organization across `Projects`, `ProjectsRuntime`, `Research`, and `SideProjects`.

## Using it in Codex

Invoke it directly in the composer with `@workspace-governor`, then describe the repo move or path audit you want.
For audit-style requests, it should run the full non-mutating assessment first, then surface the issues before asking about any changes.

## Safe workflow

1. `assess --repo <path>`
2. review classification, doc contract, rewrite candidates, machine-readable move plan, and publish-preview findings together
3. if the assessment or audit contains planned moves, run `apply --audit <json>`
4. if apply moved anything, run `verify --manifest <json> [--test-command ...]`

## Publish workflow

1. `publish-preview --repo <path>`
2. review public-doc rewrites and the publish candidate manifest
3. if public docs were auto-rewritten, review them explicitly
4. `publish --repo <path> --approve-doc-review`

The publish flow assumes:

- code lives under `~/Projects/<slug>`
- runtime-only artifacts live under `~/ProjectsRuntime/<slug>`
- cloud homes live under `~/Library/CloudStorage/OneDrive-Personal/Research/<slug>` or `~/Library/CloudStorage/OneDrive-Personal/SideProjects/<slug>`
- ordinary software repos without strong managed-layout signals stay in a neutral `Projects` cloud home instead of being forced into a research path
- public docs stay portable
- `AGENTS.md` carries private operational topology

Published artifacts are copied into dated cloud snapshots under `<cloud-home>/Analysis/<snapshot-id>`.

## Dual-doc contract

Managed projects should keep:

- public `README*` and public `docs/` portable and publish-safe
- private path truth in `AGENTS.md`
- project-specific publish overrides in `analysis_registry.yaml` when present, with `AGENTS.md` as fallback

`workspace-governor` uses `documentation-wizard` to auto-rewrite public docs that leak maintainer-only infrastructure such as `OneDrive`, `~/ProjectsRuntime`, or `/Users/...`. Publish then pauses until that rewrite has been reviewed.

## Publish policy

- a global denylist excludes logs, caches, test output, diagnostics, runtime-only bundles, and similar intermediates by default
- projects can add denylist overrides in `analysis_registry.yaml`
- publish is a promotion step from runtime to cloud; it is not normal execution in cloud storage

## Failure recovery

- backups are kept under `~/ProjectsRuntime/workspace-governor/backups`
- failed staged moves keep the source tree intact
- failed post-copy verification rolls back the destination copy before the source is touched
- rewrite planning is reported separately from file moves

## Limits

- rewrite discovery is heuristic and does not auto-edit files
- ambiguous project classification still requires explicit user input
- weakly signaled ordinary repos are treated as general software projects instead of being pushed into Research/SideProjects by default
- destinations must be absent before apply; no automatic merge is attempted
- repos that are already in the canonical layout may legitimately produce no move plan; in that case `apply` is a no-op, not an error
- publish sanitization is rule-based and should still be reviewed by a human before final publish

## Helper validation

Run `scripts/workspace_governor.py validate` to confirm the home plugin bundle is in place.
Keep the single source tree for this plugin at `~/.codex/plugins/workspace-governor`.
Use the personal marketplace at `~/.agents/plugins/marketplace.json`; do not maintain a second repo-local plugin copy.

## Deployment

From the home plugin workspace root (`~/.codex/plugins`), run `python3 scripts/deploy_plugins.py install` to refresh the personal marketplace manifest under `~/.agents/plugins/marketplace.json`. This workflow keeps `~/.codex/plugins` as the only source tree and does not copy plugins into a second location.
