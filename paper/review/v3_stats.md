# AOM v3 statistics summary

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
