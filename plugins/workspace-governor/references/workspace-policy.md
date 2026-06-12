# Workspace Policy

Use this reference for detailed workspace-governor behavior.

## Canonical Layout

- source code: `~/Projects/<slug>`
- runtime artifacts: `~/ProjectsRuntime/<slug>`
- research cloud homes: `~/Library/CloudStorage/OneDrive-Personal/Research/<slug>`
- side project cloud homes: `~/Library/CloudStorage/OneDrive-Personal/SideProjects/<slug>`

General software repos without strong managed-layout signals stay neutral rather than being forced into Research or SideProjects.

## Safe Flow

1. `assess --repo <path>`
2. review classification, doc contract, rewrite candidates, move plan, and publish preview
3. run `apply --audit <json>` only for approved moves
4. run `verify --manifest <json>` after apply

## Publish Flow

1. `publish-preview --repo <path>`
2. review public-doc rewrites and publish candidates
3. run `publish --repo <path> --approve-doc-review`

Publish copies runtime artifacts into dated cloud snapshots. It does not run normal analysis execution in cloud storage.

The publish flow assumes:

- code lives under `~/Projects/<slug>`
- runtime-only artifacts live under `~/ProjectsRuntime/<slug>`
- cloud homes live under `~/Library/CloudStorage/OneDrive-Personal/Research/<slug>` or `~/Library/CloudStorage/OneDrive-Personal/SideProjects/<slug>`
- ordinary software repos without strong managed-layout signals stay in a neutral `Projects` cloud home
- public docs stay portable and `AGENTS.md` carries private operational topology

Published artifacts are copied into dated cloud snapshots under `<cloud-home>/Analysis/<snapshot-id>`.

## Dual-Doc Contract

Managed projects should keep:

- public `README*` and public `docs/` portable and publish-safe
- private path truth in `AGENTS.md`
- project-specific publish overrides in `analysis_registry.yaml` when present, with `AGENTS.md` as fallback

`workspace-governor` uses `documentation-wizard` to auto-rewrite public docs that leak maintainer-only infrastructure. Publish pauses until that rewrite has been reviewed.

## Publish Policy

- a global denylist excludes logs, caches, test output, diagnostics, runtime-only bundles, and similar intermediates by default
- projects can add denylist overrides in `analysis_registry.yaml`
- publish is a promotion step from runtime to cloud; it is not normal execution in cloud storage

## Failure Recovery

- backups are kept under `~/ProjectsRuntime/workspace-governor/backups`
- failed staged moves keep the source tree intact
- failed post-copy verification rolls back the destination copy before the source is touched
- rewrite planning is reported separately from file moves

## Limits

- rewrite discovery is heuristic and does not auto-edit files
- ambiguous project classification still requires explicit user input
- weakly signaled ordinary repos are treated as general software projects
- destinations must be absent before apply; no automatic merge is attempted
- repos already in the canonical layout may legitimately produce no move plan
- publish sanitization is rule-based and should still be reviewed by a human

## Helper Validation

Run `scripts/workspace_governor.py validate` to confirm the plugin bundle is registered and its manifest, skill, dependencies, and assets are present.
