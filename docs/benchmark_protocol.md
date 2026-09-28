# Research benchmark protocol

Use explicit cohort, input and output paths with the generic runners under
`benchmarks/`. Fit preprocessing and select hyperparameters on training folds
only; reserve the held-out partition for final evaluation. Record seeds, split
indices, operator banks, search budgets and the full numerical environment.

Compare methods with matched inputs, folds, resource limits and metrics.
Measure the complete search, refit and prediction workflow, and report missing
results or failures alongside scores. Model-fit counts alone do not measure
wall-clock performance.

Frozen publication cohorts, paper-specific protocols and result aggregations
are maintained privately in `nirs4all-drafts`. See
[../benchmarks/README.md](../benchmarks/README.md) and
[../REPRODUCTION.md](../REPRODUCTION.md) for the public workflow.
