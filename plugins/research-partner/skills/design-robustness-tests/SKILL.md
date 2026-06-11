---
name: design-robustness-tests
description: Designs tests that catch non-regressive, scientifically meaningful failure modes in analyses and pipelines.
---

Design:
- unit tests
- integration tests
- regression tests
- perturbation tests
- invariance tests
- simulation and falsification tests

Prioritize tests that detect:
- silent data loss
- incorrect endpoint assignment
- incorrect censoring logic
- instability from sparse categories
- row-order dependence
- path-dependent output changes
- drift between runtime and published outputs
