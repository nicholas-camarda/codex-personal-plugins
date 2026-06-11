---
name: design-robustness-tests
description: Use when an analysis needs tests that catch scientifically meaningful implementation, estimand, data, or artifact regressions.
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
