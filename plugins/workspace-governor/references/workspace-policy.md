# Workspace Policy

Use this reference for detailed workspace-governor behavior.

## Canonical Layout

Active project machinery lives under `~/Workspaces/<project>/`.

Each managed workspace is itself the Git repository. At its root:

- `runtime/` holds local heavy intermediates and generated scratch artifacts.
- `archive/` holds local retired workspace material.
- `manifest.yaml` records path ownership, old aliases, project category, and verification commands.

None of these three is tracked. The project `.gitignore` lists them anchored to the root (`/runtime/`, `/archive/`, `/manifest.yaml`), the global `~/.config/git/ignore` lists them too, and `.git/hooks/pre-commit` links `~/.config/git/hooks/workspace-guard`, which refuses them and data files outside `tests/`. Nested folders with the same names, such as `openspec/changes/archive/`, are not affected.

Git worktrees, whether manual, Codex or Claude Code, go under `.claude/worktrees/<task>/`, which is ignored. Code resolves `runtime/` from the main checkout, never from the current worktree. There is no `source/` subfolder and no top-level `worktrees/` folder.

Durable cloud records live under `~/Library/CloudStorage/OneDrive-Personal/Project Vault/<category>/<project>/`.

The residency administrative root remains `~/Library/CloudStorage/OneDrive-Personal/residency`.

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

The publish flow uses the workspace `runtime/` directory for runtime-only artifacts and writes durable records under the project's configured `Project Vault` home. Public docs stay portable and `AGENTS.md` carries private operational topology.

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

- backups are kept under `~/Workspaces/_system/workspace-governor/backups`
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
