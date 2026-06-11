---
name: inspect-analysis-artifacts
description: Reconstructs the actual analysis inputs, outputs, code path, and artifact locations before any methods review.
---

Use this skill first when reviewing an analysis.

Goals:
- find the concrete data objects used by the analysis
- map source repo, runtime artifacts, and published outputs
- identify the code path from raw/derived inputs to reported outputs
- identify the exact files that support the result under discussion

Always check:
- repository AGENTS.md
- analysis_registry.yaml
- scripts, configs, and tests
- runtime and published artifact directories if declared

Produce:
- canonical path map
- analysis entrypoint
- input artifacts
- runtime artifacts
- final published outputs
- missing or inconsistent path assumptions
