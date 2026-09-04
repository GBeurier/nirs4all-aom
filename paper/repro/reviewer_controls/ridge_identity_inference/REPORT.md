# AOM-Ridge identity-only corrective inference

The matched contrast changes only the operator bank: compact nine-operator AOM-Ridge versus identity-only Ridge. Both arms use the same five folds, seeds, centering, trace-relative alpha grid, selection rule and external test split. The source-family row is the primary inferential unit; task-row inference is a sensitivity. Tests rank log RMSEP ratios.

The broader archived-default comparison uses the largest available pair but differs in tuning protocol and is therefore secondary.

| Scope | Unit | N | Median ratio | 95% bootstrap CI | W/T/L | Wilcoxon log-ratio p2 | Sign p2 |
|---|---|---:|---:|---:|---:|---:|---:|
| matched_identity | source family | 15 | 0.969 | 0.955--0.999 | 12/0/3 | 6.71e-03 | 0.035 |
| matched_identity | task row | 32 | 0.974 | 0.961--0.996 | 23/0/9 | 1.14e-03 | 0.020 |
| broader_archived_default | source family | 22 | 0.978 | 0.877--0.989 | 21/0/1 | 1.43e-06 | 1.10e-05 |
| broader_archived_default | task row | 52 | 0.974 | 0.951--0.991 | 41/0/11 | 1.04e-05 | 3.59e-05 |
