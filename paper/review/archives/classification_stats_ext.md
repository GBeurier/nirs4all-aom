# AOM classification statistics — extended (both families)

## AOM-PLS-DA vs PLS-DA-standard (16 datasets cohort)

| Comparison | N | Delta bal acc | 95% CI | Wins | Wilcoxon p_Holm |
|---|---:|---:|---|---|---|
| AOM-PLS-DA-global-nipals-adjoint vs PLS-DA | 13 | 0.030 | 0.000--0.111 | 8/13 | 0.211 |
| POP-PLS-DA-nipals-adjoint vs PLS-DA | 13 | -0.037 | -0.098--0.048 | 5/13 | 0.685 |
| **AOM-PLS-DA-global-simpls-covariance vs PLS-DA** | 13 | **0.159** | 0.129--0.422 | **12/13** | **0.007** |
| **POP-PLS-DA-simpls-covariance vs PLS-DA** | 13 | **0.052** | 0.035--0.275 | **11/13** | **0.018** |

## AOM-Ridge-Cls vs PLS-DA-standard (overlap with PLS-DA cohort)

| Comparison | N | Delta bal acc | 95% CI | Wins | Wilcoxon p (raw → Holm) |
|---|---:|---:|---|---|---|
| **AOMRidgeCls-active-compact vs PLS-DA** | 14 | **+0.163** | 0.131--0.254 | **14/14** | 0.000 → 0.001 |
| **AOMRidgeCls-branch_global-compact vs PLS-DA** | 14 | **+0.169** | 0.128--0.267 | **13/14** | 0.000 → 0.000 |
| **AOMRidgeCls-global-compact vs PLS-DA** | 14 | **+0.175** | 0.139--0.271 | **13/14** | 0.000 → 0.000 |
| **AOMRidgeCls-mkl-compact vs PLS-DA** | 14 | **+0.163** | 0.127--0.254 | **13/14** | 0.000 → 0.001 |
| **AOMRidgeCls-superblock-compact vs PLS-DA** | 14 | **+0.165** | 0.135--0.257 | **14/14** | 0.000 → 0.000 |

## Median absolute balanced accuracy

- PLS-DA-standard: median = 0.4524 (N=16)
- AOMRidgeCls-active-compact: median = 0.5954 (N=14)
- AOMRidgeCls-branch_global-compact: median = 0.6048 (N=14)
- AOMRidgeCls-global-compact: median = 0.6097 (N=14)
- AOMRidgeCls-mkl-compact: median = 0.5840 (N=14)
- AOMRidgeCls-superblock-compact: median = 0.6030 (N=14)

- AOM-PLS-DA-global-simpls-covariance: median = 0.6246 (N=13)