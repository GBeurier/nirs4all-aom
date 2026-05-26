# nirs4all-aom benchmarks

This directory holds the cohort runners that produced the paper's results,
the cohort manifests, and the paper-tied result CSVs.

## Layout

```
benchmarks/
├── pls/                              # AOM-PLS runners
│   ├── run_aompls_benchmark.py       # full AOM-PLS / POP-PLS sweep
│   ├── run_smoke_benchmark.py        # 11-dataset smoke
│   ├── run_smoke_cohort.py           # cohort-driven smoke
│   ├── run_extended_benchmark.py     # operator-explorer variants
│   ├── run_deep_bank_benchmark.py    # deep-chain ablation
│   ├── compare_with_tabpfn_master.py # comparison vs TabPFN-HPO baselines
│   ├── build_cohorts.py              # cohort manifest builder (developer)
│   ├── summarize_results.py          # post-run summariser
│   ├── cohort_regression.csv         # 61-row regression cohort
│   └── cohort_classification.csv     # 17-row classification cohort
├── ridge/                            # AOM-Ridge runners
│   ├── run_aomridge_benchmark.py
│   ├── run_aomridge_classification.py
│   ├── d_a_001_paired_stats.py
│   ├── d_a_001_audit20_paired_stats.py
│   ├── summarize_aomridge_results.py
│   └── scenarios/configs/            # JSON ablation configs
├── fast/                             # FastAOM runners
│   ├── run_fast_aom_benchmark.py
│   ├── compare_to_baselines.py
│   └── headline_comparison.py
└── runs/                             # paper-tied results (read-only ground truth)
    ├── pls/paper_aom_aompls_da_seeds012/
    ├── ridge/paper_aom_aomridge_seeds012/
    ├── ridge/paper_aom_aomridge_cls_seeds012/
    ├── ridge/all54_headline/
    ├── ridge/*.csv                   # 12 cohort manifests
    └── scenarios/                    # baseline + HPO + multi-seed AOM-PLS runs
        ├── paper_aom_aompls_seed{0,1,2}/
        ├── paper_aom_aompls_seeds012/
        ├── paper_aom_fastaom_seed0/
        ├── paper_aom_fastaom_full60_seed0/
        ├── paper_aom_linear_hpo_full_cartesian_default_cv5_all/
        ├── paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/
        └── paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/
```

## How a runner is invoked

Every runner takes the cohort CSV + the destination workspace + flags.
Example (AOM-PLS smoke on 3 datasets):

```bash
python benchmarks/pls/run_smoke_benchmark.py \
    --cohort benchmarks/pls/cohort_regression.csv \
    --workspace /tmp/aompls_smoke \
    --datasets Beer_OriginalExtract_60_KS Corn_Oil_80_ZhengChenPelegYbaseSplit
```

The runner writes `results.csv` plus per-variant logs. Aggregation across
runs is done by `paper/review/aggregate_stats.py`, which reads the CSVs
under `benchmarks/runs/` and produces the LaTeX tables and figures under
`paper/{tables,figures}/`.

## Data dependency

The runners require the NIR datasets themselves, which are not shipped with
`nirs4all-aom` (they live in `nirs4all/sample_data/` and external sources).
The paper-tied result CSVs under `benchmarks/runs/` are the artefacts that
allow stats / figures to be regenerated without re-running the (multi-hour)
benchmark.

## Cohort manifests

Cohorts shipped here (lightweight CSVs):

- `runs/ridge/all53_no_lucas_cohort.csv`, `all54_sorted_cohort.csv`,
  `all57_cohort.csv`, `curated_cohort.csv`, `diverse_cohort.csv`,
  `diverse11_cohort.csv`, `diverse_giants_only_cohort.csv`,
  `diverse_no_giants_cohort.csv`, `diverse_no_species_cohort.csv`,
  `N_woOutlier_only_cohort.csv`, `alpine_only_cohort.csv`,
  `giants_only_cohort.csv`
- `paper/review/cohort_manifest.csv` — the manifest used by the paper
  (subset of the union of all cohorts)

The strict paired intersection used in `paper/tables/table_main_results.tex`
is `N_∩ = 32` datasets, listed in
`paper/review/missing_datasets_per_variant.md`.

## Known gaps

- **AOM-Ridge headline is single-seed.** `runs/ridge/all54_headline/` is
  seed 0 only. Seeds 1 and 2 are listed as a paper-submission blocker in
  `paper/review/paper_review.md` (weakness #2). The runner to fill them is
  `benchmarks/ridge/run_aomridge_benchmark.py` invoked with seeds 1, 2.
- **HPO denominator collapse.** PLS-TabPFN-HPO and Ridge-TabPFN-HPO cover
  ~36 datasets each; the strict intersection is N=32. The list of missing
  datasets is in `paper/review/missing_datasets_per_variant.md`.
