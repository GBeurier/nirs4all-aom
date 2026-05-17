# AOM final statistics summary

## Workspaces ingested
- aom_pls_seeds012 (1485 rows)
- aom_pls_da_seeds012 (240 rows)
- aom_ridge_top5_seeds012 (376 rows)
- aom_ridge_cls_seeds012 (210 rows)
- aom_ridge_headline (534 rows)
- linear_default_cv5 (360 rows)
- pls_hpo_seed0 (38 rows)
- pls_hpo_seed1 (38 rows)
- pls_hpo_seed2 (38 rows)
- ridge_hpo_seed0 (37 rows)
- ridge_hpo_seed1 (37 rows)
- ridge_hpo_seed2 (37 rows)

## Pre-registered paired comparisons

| Comparison | N | Median effect | 95% CI | Wins | Wilcoxon p_Holm | Cliff's delta |
| --- | ---: | --- | --- | --- | --- | ---: |
| ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO | 32 | ratio=1.002 | 0.976-1.035 | 15/32 (ties 0) | 0.861 | 0.002 |
| ASLS-AOM-compact-cv5 vs PLS-default | 32 | ratio=0.985 | 0.929-1.018 | 20/32 (ties 0) | 0.651 | -0.029 |
| AOM-compact-cv5 vs PLS-default | 32 | ratio=0.991 | 0.970-1.000 | 22/32 (ties 0) | 0.335 | -0.035 |
| AOMRidge-global-compact-none vs Ridge-TabPFN-HPO | 32 | ratio=0.984 | 0.934-1.022 | 19/32 (ties 0) | 0.651 | -0.023 |
| AOMRidge-Local-compact-knn50 vs Ridge-TabPFN-HPO | 23 | ratio=1.212 | 1.132-1.553 | 4/23 (ties 0) | 0.00127 | 0.176 |
| AOMRidge-Blender vs Ridge-TabPFN-HPO | 32 | ratio=0.966 | 0.918-0.985 | 25/32 (ties 0) | 0.00308 | -0.045 |
| AOMRidge-AutoSelect vs Ridge-TabPFN-HPO | 32 | ratio=0.963 | 0.929-0.996 | 22/32 (ties 0) | 0.044 | -0.039 |

## Friedman / Nemenyi
- 9 candidates on 23 datasets, chi^2=69.890, p=5.17e-12, CD@0.05=2.505.
- mean ranks (smaller is better):
  - AOMRidge-Blender-headline-spxy3: 2.65
  - AOMRidge-AutoSelect-headline-spxy3: 2.87
  - AOMRidge-global-compact-none: 3.48
  - ridge-tabpfn-hpo-60trials: 5.04
  - AOM-compact-cv5-numpy: 5.61
  - ASLS-AOM-compact-cv5-numpy: 5.70
  - pls-tabpfn-hpo-25trials: 5.74
  - pls-default-cv5: 6.13
  - AOMRidge-Local-compact-knn50: 7.78

## Runtime summary
| Variant | N | median fit | q75 fit | q90 fit | median total | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ASLS-AOM-compact-cv5-numpy | 96 | 1.43 | 5.31 | 9.26 | 1.63 | 0 |
| AOMRidge-Blender-headline-spxy3 | 32 | 727.51 | 1526.27 | 2337.22 | 728.81 | 0 |
| AOM-compact-cv5-numpy | 96 | 1.18 | 4.81 | 8.36 | 1.18 | 0 |
| AOMRidge-Local-compact-knn50 | 69 | 2.83 | 10.10 | 13.97 | 2.96 | 0 |
| AOMRidge-global-compact-none | 32 | 23.77 | 91.96 | 140.58 | 23.78 | 0 |
| AOMRidge-AutoSelect-headline-spxy3 | 32 | 514.10 | 1196.95 | 1841.96 | 514.11 | 0 |
| Ridge-tabpfn-hpo-60trials | 96 | 0.05 | 0.15 | 0.43 | 1584.00 | 0 |
| PLS-tabpfn-hpo-25trials | 96 | 0.03 | 0.13 | 0.34 | 710.81 | 0 |
| PLS-default-cv5 | 96 | 0.02 | 0.08 | 0.34 | 1.21 | 0 |

## Seed stability
| Variant | datasets | seeds | median | IQR | std | full-seed datasets | winner changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ASLS-AOM-compact-cv5-numpy | 32 | 3 | 1.3508 | 3.3653 | 166.5182 | 32 | 21 |
| AOMRidge-Blender-headline-spxy3 | 0 | 0 | nan | nan | nan | 0 | 21 |
| AOM-compact-cv5-numpy | 32 | 3 | 1.3584 | 3.2936 | 169.8555 | 32 | 21 |
| AOMRidge-Local-compact-knn50 | 0 | 0 | nan | nan | nan | 0 | 21 |
| AOMRidge-global-compact-none | 0 | 0 | nan | nan | nan | 0 | 21 |
| AOMRidge-AutoSelect-headline-spxy3 | 0 | 0 | nan | nan | nan | 0 | 21 |
| Ridge-tabpfn-hpo-60trials | 32 | 3 | 1.4840 | 3.1295 | 162.5376 | 32 | 21 |
| PLS-tabpfn-hpo-25trials | 32 | 3 | 1.7572 | 3.7109 | 166.3684 | 32 | 21 |
| PLS-default-cv5 | 32 | 3 | 1.3935 | 3.5373 | 175.1817 | 32 | 21 |

## v3 FastAOM and cartesian-HPO supplement
## Linear cartesian-HPO denominator
- Main regression comparisons use the strict intersection N_cap=32 across the eight paper variants.

## FastAOM top variants after N >= 50 filter
- FastAOM-sparse-mkr-supervised: N=50, median_rel_rmse=1.009, median_fit_time=87.77s.
- FastAOM-sparse-mkr-compact: N=50, median_rel_rmse=1.022, median_fit_time=2.48s.
- FastAOM-single-chain-compact: N=52, median_rel_rmse=1.052, median_fit_time=1.86s.

## Paired comparisons
| Comparison | N | Median ratio | CI | Wins | p_Holm |
| --- | ---: | ---: | --- | ---: | ---: |
| ASLS-AOM-compact-cv5 vs PLS-standard | 32 | 0.973 | 0.934-0.995 | 22/32 | 0.184 |
| AOM-compact-cv5 vs PLS-standard | 32 | 0.983 | 0.963-1.005 | 20/32 | 0.518 |
| AOM-default-nipals-adjoint vs PLS-standard | 32 | 1.003 | 0.966-1.049 | 16/32 | 1.000 |
| ASLS-AOM-compact-cv5 vs PLS-default | 32 | 0.985 | 0.916-1.018 | 20/32 | 1.000 |
| AOM-compact-cv5 vs PLS-default | 32 | 0.991 | 0.970-1.000 | 22/32 | 0.896 |
| AOM-default-nipals-adjoint vs PLS-default | 32 | 1.005 | 0.975-1.057 | 15/32 | 1.000 |
| ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO | 32 | 1.002 | 0.977-1.035 | 15/32 | 1.000 |
| AOM-compact-cv5 vs PLS-TabPFN-HPO | 32 | 0.990 | 0.975-1.021 | 19/32 | 1.000 |
| PLS-TabPFN-HPO vs PLS-default | 32 | 0.992 | 0.939-1.010 | 19/32 | 1.000 |
| Ridge-TabPFN-HPO vs Ridge-default | 32 | 0.962 | 0.913-1.004 | 19/32 | 1.000 |
| AOMRidge-Blender vs Ridge-default | 32 | 0.918 | 0.808-0.937 | 27/32 | 2.6e-04 |
| AOMRidge-global-compact-none vs Ridge-default | 32 | 0.974 | 0.892-0.993 | 25/32 | 0.007 |
| AOMRidge-Blender vs Ridge-TabPFN-HPO | 32 | 0.966 | 0.918-0.985 | 25/32 | 0.033 |
| AOMRidge-AutoSelect vs Ridge-TabPFN-HPO | 32 | 0.963 | 0.929-0.996 | 22/32 | 0.741 |
| AOMRidge-global-compact-none vs Ridge-TabPFN-HPO | 32 | 0.984 | 0.934-1.020 | 19/32 | 1.000 |
| AOMRidge-Local-knn50 vs Ridge-TabPFN-HPO | 23 | 1.212 | 1.051-1.550 | 4/23 | 1.000 |
| FastAOM-sparse-mkr-supervised vs PLS-standard | 32 | 0.953 | 0.903-0.980 | 23/32 | 0.741 |
| FastAOM-sparse-mkr-compact vs PLS-standard | 32 | 0.953 | 0.909-0.979 | 22/32 | 0.518 |
| FastAOM-single-chain-compact vs PLS-standard | 32 | 0.999 | 0.977-1.036 | 16/32 | 1.000 |
| FastAOM-sparse-mkr-supervised vs PLS-TabPFN-HPO | 32 | 0.993 | 0.931-1.070 | 16/32 | 1.000 |
| FastAOM-sparse-mkr-compact vs PLS-TabPFN-HPO | 32 | 0.995 | 0.919-1.066 | 16/32 | 1.000 |
| FastAOM-single-chain-compact vs PLS-TabPFN-HPO | 32 | 1.066 | 1.021-1.131 | 7/32 | 1.000 |
| FastAOM-sparse-mkr-supervised vs ASLS-AOM-compact-cv5 | 32 | 1.021 | 0.975-1.067 | 15/32 | 1.000 |

## Friedman rank, FastAOM/AOM/PLS common subset
- N=50, methods=6, chi2=29.920, p=1.53e-05.
- Mean ranks, smaller is better:
  - ASLS-AOM-compact-cv5-numpy: 2.74
  - FastAOM-sparse-mkr-supervised: 3.08
  - FastAOM-sparse-mkr-compact: 3.18
  - AOM-compact-cv5-numpy: 3.44
  - FastAOM-single-chain-compact: 4.20
  - PLS-standard-numpy: 4.36
