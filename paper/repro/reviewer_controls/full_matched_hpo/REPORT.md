# Full matched compact-bank control

The control uses the strict 32-task regression panel, seeds 0--2, the same nine operators, identical shuffled folds, exhaustive PLS component grid (1--25), 50-value Ridge alpha grid, RMSE selection and deterministic tie rule. The only difference within each pair is folded AOM versus explicit materialization before the same linear model.

Observed wall time was 23.2 min with five single-threaded workers pinned to CPUs 10--14 and GPU visibility disabled.

## Folded versus materialized

| Folds | Model | Runs | Same selection | Folded median (s) | Materialized median (s) | Mat./folded | Max prediction diff. |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | PLS | 96 | 96/96 | 1.953 | 1.203 | 0.629 | 9.470e-11 |
| 3 | Ridge | 96 | 96/96 | 4.473 | 0.507 | 0.106 | 4.947e-06 |
| 5 | PLS | 96 | 96/96 | 3.994 | 2.423 | 0.616 | 1.026e-10 |
| 5 | Ridge | 96 | 96/96 | 10.326 | 1.201 | 0.101 | 1.010e-05 |

All 384 model-run pairs passed prediction parity and selected the same operator and hyperparameter. The finite/non-finite candidate masks differed in 0 cells. Structurally unavailable PLS component cells were non-finite in both paths and were excluded from maximum-difference calculations.

## Three-fold sensitivity

| Model | Runs | Same 3/5 selection | Median RMSE 3/5 | W/T/L for 3 folds | Median time 3/5 |
|---|---:|---:|---:|---:|---:|
| PLS | 96 | 30/96 | 1.000 | 30/30/36 | 0.499 |
| Ridge | 96 | 25/96 | 1.000 | 30/25/41 | 0.472 |

Changing the fold count often changes the selected operator/hyperparameter, as expected from fold-dependent model selection, but the median external RMSE ratio remains 1.000 for both model families. Three folds roughly halve the measured folded runtime.
