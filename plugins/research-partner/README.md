# Research Partner

`@research-partner` is a local Codex plugin for data-first review of analysis repositories.

## Using it in Codex

Invoke it directly in the composer with `@research-partner`, then describe the review you want.

## Review flow

1. `review-preflight` reconstructs artifact and path truth.
2. Specialist lanes review documentation, implementation, statistics, science, literature, and robustness.
3. `review-synthesizer` merges lane outputs into one ranked review.

Preflight may hand off to `workspace-governor` dry-run when path evidence is weak. No migrations or publish steps run automatically.

## Helper script

```bash
python plugins/research-partner/scripts/research_partner.py run --repo <path> --output-dir <dir>
```

See `references/review-lanes.md` for lane routing, agent mapping, default sequences, and limits.

## Source And Deployment

This repository is the source of truth. Installed copies under `~/.codex/plugins/<plugin-name>` are deploy targets.

```bash
python scripts/deploy_plugins.py install --source-root . --home ~
```
