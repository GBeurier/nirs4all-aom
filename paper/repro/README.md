# `paper/repro/` — AOM paper reproduction entry points

The default workflow validates and re-aggregates the **frozen** benchmark artefacts shipped with the
repository. It does not fit a model and normally completes in seconds.

From the repository root:

```bash
paper/repro/reproduce.sh check
```

## Modes

| Command | Purpose | Fits models? |
| --- | --- | --- |
| `reproduce.sh check` | Validate the frozen 61-row regression cohort, 17-row classification cohort, whitelisted result files, and WebAssembly companion bundle | No |
| `reproduce.sh tables` | Regenerate the manuscript aggregation tables from frozen CSV files | No |
| `reproduce.sh figures` | Run the existing paper figure/statistics builder | No |
| `reproduce.sh paper` | Build the paper through the manuscript build script selected by `AOM_MANUSCRIPT_BUILD` | No |
| `reproduce.sh web` | Start the local WebAssembly demo and print its self-test URL | No |
| `reproduce.sh reviewer-controls` | Regenerate the real-spectrum figure, standard RPD table, HPO audits, matched PLS-DA rerun, folded/materialised controls, the RPD>=2 sensitivity and the matched compact-bank Ridge-stacking control | Yes; CPU-only, at most five workers |
| `reproduce.sh full` | Launch fresh benchmark fits into a new, explicit output directory | Yes; opt-in only |

`reproduce.sh tables` needs Python with `numpy`, `pandas`, and `scipy`. Outputs normally go to the
manuscript `tables/` directory. To test without modifying the manuscript, use a temporary directory:

```bash
AOM_MANUSCRIPT_TABLES="$(mktemp -d)" paper/repro/reproduce.sh tables
```

Useful overrides are `PYTHON`, `AOM_BENCHMARK_MASTER`, `AOM_MANUSCRIPT_TABLES`,
`AOM_MANUSCRIPT_BUILD`, `AOM_WEB_PORT`, `NIRS4ALL_DIR`, `NIRS4ALL_LAB_DIR`, and
`NIRS4ALL_DATA_DIR`.

## Fresh benchmark fits

Fresh fits are deliberately guarded because they require external datasets and many CPU-hours. They
never overwrite the frozen paper workspaces. Set the companion repositories and a new absolute output
directory explicitly:

```bash
AOM_FULL_RUN=1 \
AOM_REPRO_OUTPUT=/absolute/path/to/new-aom-reproduction \
NIRS4ALL_DIR=/absolute/path/to/nirs4all \
NIRS4ALL_LAB_DIR=/absolute/path/to/nirs4all-lab \
NIRS4ALL_DATA_DIR=/absolute/path/to/nirs4all-data \
paper/repro/reproduce.sh full
```

Add `AOM_DRY_RUN=1` to print and validate the complete command sequence without creating the output
directory or fitting any model.

`NIRS4ALL_DATA_DIR` must contain the `regression/` and `classification/` trees. The wrapper resolves
the frozen cohort paths into copied manifests inside the new output workspace and verifies every
required file before fitting. The frozen paper results remain the reference for the submitted manuscript.
A fresh run can differ in selected preprocessing chains because folds and AOM trajectories are
stochastic; comparability comes from using the documented cohorts, operator banks, folds, budgets,
and starting inputs.

## Aggregation scripts

| Script | Main output |
| --- | --- |
| `absolute_fom.py` | `table_absolute_fom.tex` |
| `classification_calibration.py` | `table_classification_calib.tex` |
| `source_family_sensitivity.py` | `table_source_family.tex` |
| `hpo_recipe_frequency.py` | `table_hpo_recipe.tex` |
| `transfer_latency.py` | `table_transfer.tex`, `table_latency.tex` |
| `hpo_union_coverage.py` | `table_hpo_coverage.tex` |
| `seed_stability.py` | `table_seed_determinism.tex` |

Inputs are the whitelisted workspaces under `benchmarks/runs/`, the frozen benchmark master selected
by `AOM_BENCHMARK_MASTER`, and `paper/review/cohort_manifest.csv`. Each script performs a numerical
sanity check before writing its LaTeX fragment.

## Corrective reviewer controls

The targeted revision controls are collected under `reviewer_controls/`. They preserve the published
external splits and write only into that directory or the paper figure/table output directories. The
matched PLS-DA runner is resumable and varies only the identity-versus-compact operator bank. The
folded/materialised controls use the same operators, folds, grids and deterministic tie rule in both
paths. The full control covers 32 tasks, three seeds and both five- and three-fold protocols. The
SPRR-inspired control fits one Ridge model per strict-linear view and a Ridge meta-model from
out-of-fold predictions; it is a same-bank ensemble comparator, not a claimed reproduction of SPRR
or PROSAC. The RPD sensitivity uses the standard test-response definition and a baseline-defined
threshold. These controls disable GPUs, cap numerical-library threads, and use at most five CPU workers,
leaving more than two logical CPUs free on the 24-thread reference workstation.

Run all corrective controls with local regression and classification data available under
`NIRS4ALL_DATA_DIR` (or the sibling `nirs4all-data` checkout):

```bash
paper/repro/reproduce.sh reviewer-controls
```

## WebAssembly companion

The online page is an interactive companion, not the source of the archived Python timings. Test the
same local bundle with:

```bash
paper/repro/reproduce.sh web
```

Then open the printed `/demo/wasm/?selftest=1` URL. The browser's compact workload commonly shows
about a 5–6× time reduction for AOM relative to its matched HPO run; this is illustrative and
workload-dependent, not a hardware-independent algorithmic speedup.
