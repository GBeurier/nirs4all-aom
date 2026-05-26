# Reproducibility runbook

Step-by-step instructions to reproduce the paper claims for
`aom_nirs` from a fresh clone. Commands assume the current working
directory is the `aom_nirs/` repo root and that `python3.11` is on
`PATH`. The companion library
[`nirs4all`](https://github.com/GBeurier/nirs4all) is only required for
the full benchmark cohort (Section 5).

All paths are relative to `aom_nirs/`.

## Section 0. Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[bench]
```

Expected runtime: 1-2 min. Installs `numpy`, `scipy`, `scikit-learn`,
`joblib`, `pybaselines`, `pandas`, `matplotlib`, `pyarrow`.

Optional extras:

```bash
pip install -e .[torch]    # GPU NIPALS / SIMPLS / superblock backends
pip install -e .[tabpfn]   # TabPFN-residual experimental stacker
pip install -e .[dev]      # pytest, pytest-cov, ruff, mypy
```

Expected output prefix:

```
Successfully installed nirs4all-aom-0.1.0 ...
```

## Section 1. Validate the install

Run a small subset of the unit tests:

```bash
pytest tests/pls/test_estimators.py -q
```

Expected runtime: 30-60 s on CPU.

Expected output prefix:

```
.........                                                                [100%]
9 passed in ...
```

If the AOM-PLS estimators are broken, this fails immediately. The full
test suite is `pytest tests/ -q` (5-10 minutes; ridge / mkr / fast all
included).

## Section 2. Synthetic smoke

`examples/paper_smoke.py` reproduces the paper's main qualitative
claims on a single 120 × 200 synthetic NIR-like dataset. It evaluates
PLS-default, AOM-PLS-simple, AOM-PLS-best, AOM-Ridge-global,
AOM-Ridge-Blender, and FastAOM-sparse-mkr, then prints test RMSE and
the selected operator(s) for each.

```bash
python examples/paper_smoke.py
```

Expected runtime: 30-90 s on CPU.

Expected output prefix:

```
== Synthetic NIR smoke ==
n=120 train / 30 test, p=200, 3 absorbance bands + baseline drift + 5% noise.

  PLS-default                   RMSE=...  ...
  AOM-PLS-simple                RMSE=...  selected_op=...
  AOM-PLS-best                  RMSE=...  selected_op=...
  AOM-Ridge-global              RMSE=...  selected_op=...
  AOM-Ridge-Blender             RMSE=...  top_candidate=...
  FastAOM-sparse-mkr            RMSE=...  chains=...
```

For one-method quickstarts see `examples/01_aom_pls_quickstart.py`,
`examples/02_aom_ridge_blender.py`, `examples/03_fastaom_quickstart.py`.
These do not benchmark; they just demonstrate the sklearn API.

## Section 3. Regenerate paper figures

The figures and the PDF are built by `paper/build.sh`. Requirements:

- `pdflatex` (TeX Live or MikTeX)
- `bibtex`
- the regenerated figures must already be in `paper/figures/` (see
  Section 4 if the tables / figures are stale)

```bash
bash paper/build.sh
```

Expected runtime: 1-3 min.

Expected output prefix:

```
This is pdfTeX, Version ...
... (pdflatex pass 1)
This is BibTeX, Version ...
... (pdflatex pass 2)
... (pdflatex pass 3)
Built paper_aom/main.pdf and paper_aom/supplement.pdf
```

The script regenerates figures via `paper/scripts/make_figures.py`, then
runs `pdflatex` + `bibtex` + two more `pdflatex` passes for both
`main.tex` and `supplement.tex`. Outputs:
`paper/main.pdf`, `paper/supplement.pdf`, plus the named copies
`paper/AOM-paper.pdf`, `paper/AOM-supplement.pdf`.

## Section 4. Re-aggregate paper statistics

Re-run the statistical aggregation against the shipped benchmark
outputs in `benchmarks/runs/scenarios/`:

```bash
python paper/review/aggregate_stats.py --partial
```

Use `--strict` to fail loudly when any expected workspace is missing
(see `paper/review/missing_datasets_per_variant.md` for the variants
known to be incomplete).

Expected runtime: 30-90 s on CPU.

Expected output prefix:

```
Loaded N rows from M workspaces.
Strict regression intersection N=32.
Missing required workspaces: ...
```

Side effects:

- LaTeX tables written to `paper/tables/`:
  `table_main_results.tex`, `table_paired_stats.tex`,
  `table_classification_main.tex`, `table_time_budget.tex`, ...
- Figures written to `paper/figures/`: `fig_results.pdf`,
  `fig_paired_rmsep_scatter.pdf`, `fig_r2_cdf.pdf`,
  `fig_accuracy_time_pareto.pdf`, ...
- Markdown summary refreshed: `paper/review/final_stats.md`.

After this step you can rebuild the PDF (Section 3) to pick up the
refreshed tables and figures.

## Section 5. Full benchmark re-run

The numerical claims of the paper (the 61-row regression cohort, the
17-row classification cohort, the 32-row strict intersection) require
the NIR datasets *and* extended compute (single-machine multi-hour).

### Data requirements

The raw spectral files are not redistributed by `aom_nirs`. They live
in `nirs4all/sample_data/` and in the external public sources cited in
`paper/main.tex` and `paper/review/cohort_manifest.csv`. Two routes:

1. Clone the companion library:
   ```bash
   git clone https://github.com/GBeurier/nirs4all.git
   ```
   The runners auto-discover `nirs4all/sample_data/` when both repos
   share the same parent directory (`aom_nirs/` and `nirs4all/`
   siblings).

2. Fetch the public sources listed in
   `paper/review/cohort_manifest.csv` (column `source_family`) one at a
   time. Local-only datasets (BERRY, ALPINE, ...) are CIRAD-internal
   and must be requested from the corresponding author.

### Compute requirements

| Variant | Median fit time | Datasets | Notes |
| --- | --- | --- | --- |
| `pls-default-cv5` | 0.02 s | 57/seed | trivial |
| `AOM-compact-cv5-numpy` | 1.18 s | 55/seed | minutes / seed |
| `ASLS-AOM-compact-cv5-numpy` | 1.43 s | 53/seed | minutes / seed |
| `pls-tabpfn-hpo-25trials` | 710.81 s median total | 36 datasets / seed | ~40 h total |
| `ridge-tabpfn-hpo-60trials` | 1584.00 s median total | 35 datasets / seed | ~50 h total |
| `AOMRidge-global-compact-none` | 23.78 s | 53 datasets, seed 0 | tens of minutes |
| `AOMRidge-Blender-headline-spxy3` | 728.81 s | 53 datasets, seed 0 | several hours |

### Commands

```bash
# AOM-PLS / POP-PLS / ASLS-AOM-PLS regression cohort, seeds 0..2:
python benchmarks/pls/run_aompls_benchmark.py --seeds 0 1 2

# AOM-Ridge headline + auto_select + Blender:
python benchmarks/ridge/run_aomridge_benchmark.py --seeds 0

# AOM-PLS-DA classification cohort:
python benchmarks/ridge/run_aomridge_classification.py --seeds 0 1 2

# FastAOM variants:
python benchmarks/fast/run_fast_aom_benchmark.py --seeds 0

# Linear default + HPO cartesian baselines:
# (re-run the runners that wrote the workspaces in benchmarks/runs/scenarios/)
```

After every run, re-aggregate (Section 4) and rebuild the PDF
(Section 3).

## Section 6. paper-review blockers still open

Two gaps must be closed before the manuscript can claim seed-stable
statistics across every variant:

1. **AOM-Ridge seeds 1 and 2.** The headline variants
   `AOMRidge-Blender-headline-spxy3`,
   `AOMRidge-AutoSelect-headline-spxy3`, and
   `AOMRidge-global-compact-none` currently ship results for seed 0
   only. See `paper/review/final_stats.md` "Seed stability" table:
   `0 full-seed datasets` for these three variants. Re-run
   `benchmarks/ridge/run_aomridge_benchmark.py --seeds 1` and
   `--seeds 2`, then re-aggregate.

2. **HPO missingness.** `pls-tabpfn-hpo-25trials` covers 36 datasets /
   seed (25 not attempted, 2 errors) and
   `ridge-tabpfn-hpo-60trials` covers 35 datasets / seed (24 not
   attempted, 2 errors). The strict-intersection denominator is
   computed from the variants that *did* succeed, so closing this gap
   raises `N_∩` above 32. The audit is in
   `paper/review/missing_datasets_per_variant.md`. The error column
   (`Input X contains NaN`, `n_components upper bound 22; Got 23`)
   indicates two distinct fixes: NaN handling in the runner pre-flight
   for the affected datasets, and lower `n_components` cap for
   small-`n` rows.

When both blockers are cleared, `paper/review/aggregate_stats.py
--partial` should report zero missing required workspaces and the
"Seed stability" table should list `seeds = 3` for every AOM-Ridge
headline variant. Only then is the paper's statistical methodology
applied identically across the eight headline rows.
