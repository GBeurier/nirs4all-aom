# Reviewer-insurance runs (optional) — A2-res, A4-res

These two runs are **optional insurance** against specific reviewer demands. The paper does not need
them: the HPO denominator is already handled by the tuned-union (59/61, `hpo_union_coverage.py`) and
the de-facto recipe is reported from the HPO selections (`hpo_recipe_frequency.py`). Run them only if
a reviewer insists on (A2) a single consistent full-HPO protocol across the whole cohort, or (A4) a
literally fixed preprocessing recipe applied uniformly.

> **Data is LOCAL (gitignored, not published):** the raw NIR spectra live at
> `nirs4all-lab/tabpfn/paper/data/regression/...` (237 dataset dirs; `;`-separated, header =
> wavelengths, target column `Ycal`), symlinked into this repo at `benchmarks/data` (gitignored).
> So both runs are executable here. **A4-res has been run** by `fixed_recipe.py` (below) — fast.
> **A2-res is heavy** (≈150–300 core-h: 3000 PLS / 6000 Ridge fits × ~23 datasets × 3 seeds) — launch
> it on a multi-core box / cluster, not interactively.

## A4-res — pre-registered fixed conventional recipe (do this first; cheap)

> **Result (computed, `fixed_recipe.py`, 58/60 datasets):** the fixed recipe gives no systematic gain
> over plain PLS/Ridge — median paired RMSEP ratio 1.003 (PLS, 25/53) and 1.017 (Ridge, 22/52).
> Operator-adaptive AOM beats the same fixed recipe: AOM-PLS 0.980 (31/53), AOM-Ridge-global 0.949
> (34/52). Emitted to `table_fixed_recipe.tex`; integrated in the supplement + main §3.5. The two
> skipped datasets (`FinalScore_grp70_30_scoreQ`, `Tleaf_grp70_30`) have non-finite spectra. Re-running
> the script reuses `fixed_recipe_results.csv` (cache) so only the aggregation/table is regenerated.

Apply ONE preprocessing recipe to every cohort dataset, tuning only `n_components` by 5-fold CV — no
preprocessing search. **Pre-register the recipe before looking at scores:**

```
SNV  →  Savitzky–Golay 1st derivative (window = 15, polyorder = 2)  →  PLS
n_components ∈ {1, …, min(20, n_train − 1)} chosen by 5-fold CV (one-SE rule)
```
(Window 15/order 2 is the conventional default; note the HPO most-selected SG was window 31 — report
both if asked. Ridge twin: same recipe → Ridge, α by 5-fold CV.)

Runnable shape (fill in the cohort/data path; uses the `nirs4all` pipeline API):
```python
import nirs4all
from nirs4all.operators.transforms.nirs import StandardNormalVariate, SavitzkyGolay
from sklearn.cross_decomposition import PLSRegression
pipeline = [StandardNormalVariate(),
            SavitzkyGolay(window_length=15, polyorder=2, deriv=1),
            {"model": PLSRegression()}]   # n_components swept by the runner's CV
# loop the 61 regression datasets from cohort_regression.csv (train_path/test_path/...)
# emit one RMSEP per dataset, seeds 0/1/2 → paper/review/ + a table fragment.
```
Output target: `manuscript/tables/table_fixed_recipe.tex` (PLS-fixed / Ridge-fixed vs the existing
PLS-default / PLS-HPO columns on the paired denominator). Then re-run
`paper/repro/source_family_sensitivity.py` if you add it to the headline family.

## A2-res — strict single-protocol full-HPO on the not-attempted datasets
Re-run the existing PLS-/Ridge-TabPFN-HPO runner (the one that produced
`benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_{pls,ridge}-tabpfn-hpo-*`) on the
datasets currently "not attempted", **seeds 0/1/2**, after two fixes:
- NaN pre-flight: drop/zero-impute non-finite spectral columns before the search (fixes
  `ValueError: Input X contains NaN` on the two FUSARIUM targets — or leave them out, they fail every
  linear method).
- `n_components` cap: clamp to `≤ n_train − 1` (fixes `Firmness_spxy70`: "upper bound 22, got 23").

Dataset list = the "not attempted" rows in `../../review/missing_datasets_per_variant.md`
(≈23 for PLS-HPO, ≈24 for Ridge-HPO). Goal: lift the strict full-HPO intersection from `N_cap=35`
toward the full cohort, so the headline can be quoted on a single consistent protocol if required.
After the run, re-run `paper/repro/hpo_union_coverage.py` and `aggregate_stats.py` to refresh the
denominators and `table_main_results`.

## Decision
Default = **do not run**; present the union (59/61) and the de-facto-recipe table. Keep these two
commands ready as the reviewer-rebuttal package.
