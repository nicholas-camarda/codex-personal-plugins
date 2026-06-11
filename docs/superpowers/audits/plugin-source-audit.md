# Codex Plugin Source Audit

## Expected Source Of Truth

- `/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json`
- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/.codex-plugin/plugin.json`
- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/.codex-plugin/plugin.json`
- `/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/.codex-plugin/plugin.json`
- Installed copies under `/Users/ncamarda/.codex/plugins/<plugin-name>/` are deploy targets, not source.

## Project Plugin Definitions

/Users/ncamarda/Projects/codex-personal-plugins/.agents/plugins/marketplace.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/assess-literature-support/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/design-robustness-tests/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/research-partner/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-documentation-consistency/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-implementation-validity/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/review-statistical-validity/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/research-partner/skills/synthesize-review/SKILL.md
/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/.codex-plugin/plugin.json
/Users/ncamarda/Projects/codex-personal-plugins/plugins/workspace-governor/skills/workspace-governor/SKILL.md
/Users/ncamarda/Projects/endolaserless/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/endolaserless/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/endolaserless/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/endolaserless/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/endolaserless/.github/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/endolaserless/.github/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/endolaserless/.github/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/endolaserless/.github/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.cursor/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.cursor/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.cursor/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.cursor/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.github/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.github/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.github/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/endotheliosis_quantifier/.github/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/ffbayes/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/ffbayes/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/ffbayes/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/ffbayes/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/ffbayes/.github/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/ffbayes/.github/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/ffbayes/.github/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/ffbayes/.github/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/mmBayes/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/mmBayes/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/mmBayes/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/mmBayes/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/mmBayes/.github/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/mmBayes/.github/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/mmBayes/.github/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/mmBayes/.github/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/proteome_profiler/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/proteome_profiler/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/proteome_profiler/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/proteome_profiler/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.codex/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.codex/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.codex/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.codex/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.cursor/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.cursor/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.cursor/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.cursor/skills/openspec-propose/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.github/skills/openspec-apply-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.github/skills/openspec-archive-change/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.github/skills/openspec-explore/SKILL.md
/Users/ncamarda/Projects/uveal_melanoma/.github/skills/openspec-propose/SKILL.md

## Personal Install Definitions

/Users/ncamarda/.codex/plugins/documentation-wizard/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/documentation-wizard/skills/documentation-wizard/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/research-partner/skills/assess-literature-support/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/design-robustness-tests/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/inspect-analysis-artifacts/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/research-partner/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-documentation-consistency/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-implementation-validity/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-scientific-interpretation/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/review-statistical-validity/SKILL.md
/Users/ncamarda/.codex/plugins/research-partner/skills/synthesize-review/SKILL.md
/Users/ncamarda/.codex/plugins/workspace-governor/.codex-plugin/plugin.json
/Users/ncamarda/.codex/plugins/workspace-governor/skills/workspace-governor/SKILL.md

## Cleanup Decision

Allowed source repo: `/Users/ncamarda/Projects/codex-personal-plugins`.
Allowed remote: `https://github.com/nicholas-camarda/codex-personal-plugins.git`.
Allowed personal install roots: `/Users/ncamarda/.codex/plugins/documentation-wizard`, `/Users/ncamarda/.codex/plugins/research-partner`, `/Users/ncamarda/.codex/plugins/workspace-governor`.
No curated cache files are source of truth.
Duplicate authored plugin definitions must be merged into canonical source if useful, then removed from discovery paths.
Conflict detector passed before implementation continued.
