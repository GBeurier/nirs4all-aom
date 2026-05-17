# Benchmark protocol

This document describes the protocol used in the Talanta paper
*Operator-adaptive PLS and Ridge calibration for NIR spectroscopy* to
benchmark `aom_nirs` against PLS and Ridge baselines. Companion
[`nirs4all`](https://github.com/GBeurier/nirs4all) provides the
end-to-end dataset loaders used by the runners.

## Cohort

The benchmark cohort is intentionally heterogeneous: leaf physiology,
fruit quality, grain and seed traits, dairy, beverages, meat quality,
petroleum, soil amendments, wood products, pharmaceutical tablets.
Several source databases contribute more than one response variable, so
a row denotes a concrete prediction or classification task, not just a
spectral database.

- 61 regression rows.
- 17 classification rows.
- **N_∩ = 32** strict intersection of regression rows for which every
  one of the eight headline paper variants has a valid result.
- **53-dataset** AOM-Ridge headline denominator: number of rows on
  which both `AOMRidge-global-compact-none` and
  `AOMRidge-Blender-headline-spxy3` produced results.
- 13-row paired classification denominator for
  `AOM-PLS-DA-global-simpls-covariance`.

Cohort manifest: `paper/review/cohort_manifest.csv`. Missing-cell audit:
`paper/review/missing_datasets_per_variant.md`.

The cohort is composed (regression) of: median `n = 402` samples,
median `p = 1023` spectral variables. Classification: median `n = 511`,
median `p = 1951`, median `C = 2` classes, median largest-class share
`0.513`.

The raw spectral files themselves are *not* redistributed inside
`aom_nirs`. They live in `nirs4all/sample_data/` and in external public
sources cited in `paper/main.tex`. Reproducing the full cohort requires
either a working `nirs4all` checkout or fetching the public datasets
from their original locations.

## Splits

| Task | Split | Notes |
| --- | --- | --- |
| Regression | SPXY (`KennardStoneSplitter` / `SPXYSplitter`) when no source-defined split exists | Single split per dataset, with the source-defined train/test pair preserved when present. |
| Classification | Stratified SPXY | Preserves class proportions in train/test. |
| External test sets | Held out from every preprocessing, operator, α, and component selection. | No outlier removal applied; calibration and test samples kept as supplied. |

The selection-set CV folds inside the calibration set use either
sklearn `KFold(shuffle=True, random_state=seed)` or the
chemistry-aware `SPXYFold` / `RepeatedSPXYFold` from
`aom_nirs/ridge/cv.py` (`split_aware_cv.py`). The AOM-Ridge headline
selector uses `outer_cv_kind="spxy"` with `outer_cv_splits=3`.

## Seeds

The PLS / Ridge / AOM-PLS / HPO families ran under three seeds
(`seeds 0, 1, 2`):

| Family | Seeds |
| --- | --- |
| `pls-default-cv5`, `pls-tabpfn-hpo-25trials` | 0, 1, 2 |
| `ridge-default-cv5`, `ridge-tabpfn-hpo-60trials` | 0, 1, 2 |
| `AOM-compact-cv5-numpy`, `ASLS-AOM-compact-cv5-numpy` | 0, 1, 2 |

The headline **AOM-Ridge Blender** (`AOMRidge-Blender-headline-spxy3`)
and `AOMRidge-AutoSelect-headline-spxy3` and
`AOMRidge-global-compact-none` currently ship results for **seed 0
only** (see `paper/review/final_stats.md` "Seed stability" table: 0
full-seed datasets for these three variants). This is a known Talanta
review blocker. Before journal submission, seeds 1 and 2 must be
filled to enable the same paired-stats methodology used for the PLS
families.

The headline regression workspace
`paper_aom_aompls_seeds012/` covers the AOM-PLS / ASLS-AOM-PLS results
across all three seeds; the AOM-Ridge headline workspace is the
single-seed `all54_headline/` run. See
`paper/review/missing_datasets_per_variant.md` for the per-variant
status table.

## Selection

- Inner selection: 5-fold CV (default `cv=5`) on the calibration set.
- Optional one-SE rule: `CriterionConfig(one_se_rule=True)`. Among
  candidates within `best_score + std/sqrt(n_folds)`, prefer the
  smallest `k` and (when the bank starts with `IdentityOperator`) the
  identity-leaning operator.
- Optional CV repeats: `CriterionConfig(repeats=R)` with random-state
  offset `+r` per repeat. Reduces selection variance by `sqrt(R)`.
  Custom `cv_splitter`s (e.g. `SPXYFold`) must use `repeats=1` because
  they are deterministic.
- Auto-prefix: `auto_prefix=True` evaluates every prefix
  `k ∈ {1, ..., n_components_max}` and picks the argmin. For `cv` and
  `holdout` this is one full fit per fold; for `approx_press` one full
  fit then prefix-coefficient evaluation.

## Statistical methodology

All paired statistics use the *strict intersection* `N_∩ = 32` for the
main regression comparisons. Numbers in `paper/review/final_stats.md`
and `paper/review/v3_stats.md` are produced by
`paper/review/aggregate_stats.py`:

- **Paired Wilcoxon signed-rank test** (one-sided, `lower-RMSEP favours
  row method`) with **Holm correction** within the displayed family.
- **Friedman test** across `k` methods on the common-subset rows, with
  **Nemenyi critical-distance CD@0.05** for the ranks plot.
- **Cliff's delta** as the rank-based effect size.
- **95% confidence intervals on median RMSEP ratios** via the paired
  bootstrap implemented in
  `aggregate_stats.py::_bootstrap_median_ci`.

The metric for regression is **RMSEP** on the held-out test set.
Because response scales differ across traits, aggregate regression
results report **paired RMSEP ratios** `RMSEP(method) / RMSEP(ref)`.
Classification uses **balanced accuracy**.

The PLS and Ridge HPO baselines are intentionally strong and
expensive. `PLS-TabPFN-HPO` enumerates 600 preprocessing combinations
with 5 trials per combination (3000 trial fits / dataset / seed);
`Ridge-TabPFN-HPO` uses 10 trials per combination (6000 fits).

## Variant naming

The runner labels follow the convention

```
<family>-<bank>-<criterion>-<engine>
```

Examples and the eight paper variants:

| Paper label | Runner key |
| --- | --- |
| PLS-default | `pls-default-cv5` |
| PLS-HPO | `pls-tabpfn-hpo-25trials` |
| AOM-PLS (simple) | `AOM-compact-cv5` |
| AOM-PLS (best) | `ASLS-AOM-compact-cv5` |
| Ridge-default | `ridge-default-cv5` |
| Ridge-HPO | `ridge-tabpfn-hpo-60trials` |
| AOM-Ridge (simple) | `AOMRidge-global-compact-none` |
| AOM-Ridge (best, headline) | `AOMRidge-Blender-headline-spxy3` |

Classification headline: `AOM-PLS-DA-global-simpls-covariance`.
FastAOM top variants (v3 supplement): `FastAOM-sparse-mkr-supervised`,
`FastAOM-sparse-mkr-compact`, `FastAOM-single-chain-compact`.

## Where to find each piece

### Runners

```
benchmarks/pls/
  run_aompls_benchmark.py        # AOM-PLS + POP-PLS regression cohort
  run_smoke_benchmark.py         # quick smoke pass
  run_smoke_cohort.py            # 11-dataset smoke cohort
  run_extended_benchmark.py      # extended PLS variants
  run_deep_bank_benchmark.py     # deep-bank composed operators
  build_cohorts.py               # cohort manifest construction
  summarize_results.py           # result aggregation
  cohort_regression.csv          # the regression cohort row list
  cohort_classification.csv      # the classification cohort row list

benchmarks/ridge/
  run_aomridge_benchmark.py      # AOM-Ridge headline + auto_select + blender
  run_aomridge_classification.py # AOM-Ridge classification
  summarize_aomridge_results.py
  d_a_001_paired_stats.py        # paired-stats sanity check
  d_a_001_audit20_paired_stats.py

benchmarks/fast/
  run_fast_aom_benchmark.py      # FastAOM (single / hard / soft / sparse-MKR)
  compare_to_baselines.py
  headline_comparison.py
```

### Outputs

```
benchmarks/runs/scenarios/
  paper_aom_aompls_seed0/             # AOM-PLS family, seed 0
  paper_aom_aompls_seed1/
  paper_aom_aompls_seed2/
  paper_aom_aompls_seeds012/          # aggregated results.csv
  paper_aom_fastaom_seed0/
  paper_aom_fastaom_full60_seed0/
  paper_aom_linear_hpo_full_cartesian_default_cv5_all/
  paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed0/  (and 1, 2)
  paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed0/ (and 1, 2)
```

Each scenario directory contains the runner manifest, per-row CSVs,
logs, and an aggregated `results.csv` consumed by `aggregate_stats.py`.

### Statistics aggregation

`paper/review/aggregate_stats.py` ingests the workspace CSVs, computes
the paired tables, Friedman ranks, seed stability, and runtime
summary, and emits the LaTeX tables and figures referenced by the
manuscript. Outputs land in `paper/tables/` and `paper/figures/`. The
markdown summary it produces is `paper/review/final_stats.md`
(refreshed each time the script runs against an updated workspace).

## Reported numbers

`paper/review/final_stats.md` is the source of truth for the headline
numbers cited in the paper. The headline pairings (intersection
`N = 32` unless noted) include:

- `ASLS-AOM-compact-cv5 vs PLS-default`: median ratio 0.985, 20/32 wins.
- `AOM-compact-cv5 vs PLS-default`: median ratio 0.991, 22/32 wins.
- `ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO`: median ratio 1.002, 15/32 wins.
- `AOMRidge-global-compact-none vs Ridge-default`: median ratio 0.974,
  25/32 wins, Holm-adjusted `p = 0.007`.
- `AOMRidge-Blender vs Ridge-default`: median ratio 0.918, 27/32 wins,
  Holm-adjusted `p = 2.6e-4`.
- `AOMRidge-Blender vs Ridge-TabPFN-HPO`: median ratio 0.966, 25/32
  wins, Holm-adjusted `p = 0.033`.

Friedman test on the common 23-dataset subset of 9 candidates:
`chi^2 = 69.890`, `p = 5.17e-12`, `CD@0.05 = 2.505`. Mean ranks
(smaller is better) put `AOMRidge-Blender-headline-spxy3` at 2.65 and
`AOMRidge-AutoSelect-headline-spxy3` at 2.87, ahead of every other
candidate.

FastAOM v3 supplement (`paper/review/v3_stats.md`), `N >= 50` filter:

- `FastAOM-sparse-mkr-supervised`: median `rel_rmse = 1.009`, median
  fit time 87.77 s.
- `FastAOM-sparse-mkr-compact`: median `rel_rmse = 1.022`, median fit
  time 2.48 s.
- `FastAOM-single-chain-compact`: median `rel_rmse = 1.052`, median
  fit time 1.86 s.

## Reproducibility note

The cohort manifest is the only authoritative listing of the rows used
by every paper number. The strict intersection is *computed*, not
hand-curated; updating any runner's input set will re-compute it.
`aggregate_stats.py` reads the workspace CSVs directly — it does not
take per-row metadata from the manifest beyond the dataset name.
