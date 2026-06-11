---
name: synthesize-review
description: Deduplicates specialist lane outputs and turns them into one ranked final review.
---

Use this skill for the `review-synthesizer` lane after preflight and any selected specialist lanes have produced structured outputs.

Ground the synthesis with `scripts/research_partner.py bundle`.

Required output contract:
- `Scope`
- `Artifact map / evidence reviewed`
- `Findings`
- `Direct evidence vs inference`
- `Required tests / checks`
- `Recommended actions`

The synthesis should:
- merge duplicates across lanes
- keep the strongest direct evidence attached to each finding
- preserve uncertainty and lane disagreement
- end with an action list ordered by dependency and severity
