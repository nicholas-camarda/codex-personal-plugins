# Codex Plugin Source Audit

## Expected Source Of Truth

- `.agents/plugins/marketplace.json`
- `plugins/documentation-wizard/.codex-plugin/plugin.json`
- `plugins/research-partner/.codex-plugin/plugin.json`
- `plugins/workspace-governor/.codex-plugin/plugin.json`
- Installed copies under `~/.codex/plugins/<plugin-name>/` are deploy targets, not source.

## Project Plugin Definitions

.agents/plugins/marketplace.json
plugins/documentation-wizard/.codex-plugin/plugin.json
plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
plugins/research-partner/.codex-plugin/plugin.json
plugins/research-partner/skills/assess-literature-support/SKILL.md
plugins/research-partner/skills/design-robustness-tests/SKILL.md
plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
plugins/research-partner/skills/research-partner/SKILL.md
plugins/research-partner/skills/review-documentation-consistency/SKILL.md
plugins/research-partner/skills/review-implementation-validity/SKILL.md
plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
plugins/research-partner/skills/review-statistical-validity/SKILL.md
plugins/research-partner/skills/synthesize-review/SKILL.md
plugins/workspace-governor/.codex-plugin/plugin.json
plugins/workspace-governor/skills/workspace-governor/SKILL.md

## Personal Install Definitions

~/.codex/plugins/documentation-wizard/.codex-plugin/plugin.json
~/.codex/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
~/.codex/plugins/research-partner/.codex-plugin/plugin.json
~/.codex/plugins/research-partner/skills/assess-literature-support/SKILL.md
~/.codex/plugins/research-partner/skills/design-robustness-tests/SKILL.md
~/.codex/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
~/.codex/plugins/research-partner/skills/research-partner/SKILL.md
~/.codex/plugins/research-partner/skills/review-documentation-consistency/SKILL.md
~/.codex/plugins/research-partner/skills/review-implementation-validity/SKILL.md
~/.codex/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
~/.codex/plugins/research-partner/skills/review-statistical-validity/SKILL.md
~/.codex/plugins/research-partner/skills/synthesize-review/SKILL.md
~/.codex/plugins/workspace-governor/.codex-plugin/plugin.json
~/.codex/plugins/workspace-governor/skills/workspace-governor/SKILL.md

## Cleanup Decision

Allowed source repo: `the local source checkout`.
Allowed remote: `https://github.com/nicholas-camarda/codex-personal-plugins.git`.
Allowed personal install roots: `plugins/documentation-wizard`, `plugins/research-partner`, `plugins/workspace-governor`.
No curated cache files are source of truth.
Duplicate authored plugin definitions must be merged into canonical source if useful, then removed from discovery paths.
Conflict detector passed before implementation continued.
