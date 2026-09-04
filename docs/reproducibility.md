# Reproducibility runbook

Step-by-step instructions to reproduce the paper claims for
`aom_nirs` from a fresh clone. Commands assume the current working
directory is the `aom_nirs/` repo root and that `python3.11` is on
`PATH`. The companion library
[`nirs4all`](https://github.com/GBeurier/nirs4all) is only required for
the full benchmark cohort (Section 5).

All paths are relative to `aom_nirs/`.

## One-command entry points

The maintained wrapper is `paper/repro/reproduce.sh`:

```bash
paper/repro/reproduce.sh check    # read-only integrity check
paper/repro/reproduce.sh tables   # frozen-result aggregations
paper/repro/reproduce.sh web      # local WebAssembly companion
```

See `paper/repro/README.md` for all modes and path overrides. These default modes do not fit models.

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
Successfully installed nirs4all-aom-0.10.4 ...
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

The raw spectral files are not redistributed by `aom_nirs`. Prepare a
local data root containing `regression/` and `classification/` trees
with the database/dataset layout named by the frozen cohort CSV files.
Public retrieval and licence metadata are maintained in the
`nirs4all-datasets` catalogue; restricted source families must be
requested from the corresponding author under their original terms.

The full wrapper receives that root as `NIRS4ALL_DATA_DIR`, rewrites a
copy of each frozen cohort with absolute paths inside the new output
workspace, and checks every required file before any fit starts. The
`nirs4all` and `nirs4all-lab` checkouts remain separate code
dependencies supplied through `NIRS4ALL_DIR` and `NIRS4ALL_LAB_DIR`.

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

Use the guarded full-run wrapper. It refuses to start unless a new,
absolute output directory and the companion repositories are provided:

```bash
AOM_FULL_RUN=1 \
AOM_REPRO_OUTPUT=/absolute/path/to/new-aom-reproduction \
NIRS4ALL_DIR=/absolute/path/to/nirs4all \
NIRS4ALL_LAB_DIR=/absolute/path/to/nirs4all-lab \
NIRS4ALL_DATA_DIR=/absolute/path/to/nirs4all-data \
paper/repro/reproduce.sh full
```

Add `AOM_DRY_RUN=1` to inspect the complete command sequence without
creating the output directory or fitting models.

This launches the documented AOM-PLS, AOM-Ridge, classification,
FastAOM, and matched linear-HPO runners. It does not overwrite the
frozen paper workspaces. Inspect the new workspace before choosing to
re-aggregate or revise manuscript denominators.

## Section 6. Known coverage limitations

The submitted analysis reports two coverage limitations explicitly;
they are not silently imputed or treated as completed runs:

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

Future extensions may fill these cells in a new output workspace. If
they do, all denominators and inferential summaries must be regenerated
and reported as a new analysis rather than substituted silently into
the frozen submission results.
