# Workspace Governor

`@workspace-governor` is a local Codex plugin for safe workspace migration and publish-gated organization.

## Using it in Codex

Invoke it directly in the composer with `@workspace-governor`, then describe the repo move or path audit you want.

## Safe workflow

1. `assess --repo <path>`
2. review classification, doc contract, rewrite candidates, and move plan
3. `apply --audit <json>` for approved moves
4. `verify --manifest <json>` after apply

## Helper script

```bash
python plugins/workspace-governor/scripts/workspace_governor.py assess --repo <path>
```

See `references/workspace-policy.md` for publish flow, dual-doc contract, denylist policy, recovery, and limits.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```
