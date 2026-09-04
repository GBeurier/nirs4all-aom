# RPD>=2 task-quality sensitivity

Post-hoc sensitivity using the standard RPD = sample SD(y_test) / RMSEP. The primary inclusion rule is defined from Ridge-default, independently of the AOM result.

| Subset | N | Median AOM/default RMSEP ratio | 95% bootstrap CI | Wins/ties/losses | Raw two-sided Wilcoxon p |
|---|---:|---:|---:|---:|---:|
| strict_N32_all | 32 | 0.974 | 0.869--0.993 | 25/0/7 | 6.06e-04 |
| baseline_RPD_ge_2 | 13 | 0.606 | 0.496--0.933 | 12/0/1 | 0.003 |
| AOM_RPD_ge_2_audit_only | 13 | 0.606 | 0.496--0.933 | 12/0/1 | 0.003 |

Baseline- and AOM-defined RPD>=2 sets identical: True.
