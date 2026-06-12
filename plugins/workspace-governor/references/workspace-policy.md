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
