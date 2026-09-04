# Matched compact-bank Ridge stacking control

This is an SPRR-inspired same-bank control, not a faithful reproduction of SPRR or PROSAC.
Each of the nine strict-linear views has its own five-fold-tuned Ridge base learner; a five-fold-tuned Ridge meta-model combines out-of-fold base predictions. The external test split is untouched until final evaluation.

| Comparison | N | Median RMSEP ratio | 95% bootstrap CI | Wins/ties/losses | Raw two-sided Wilcoxon p |
|---|---:|---:|---:|---:|---:|
| SPRR-inspired Ridge stacking vs matched AOM-Ridge | 32 | 0.991 | 0.981--1.011 | 18/0/14 | 0.561 |
| SPRR-inspired Ridge stacking vs matched raw Ridge | 32 | 0.968 | 0.931--0.991 | 25/0/7 | 0.002 |

Wall time: 84.0 s; workers: 5; CUDA_VISIBLE_DEVICES=''.
