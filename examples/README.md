# Examples

Runnable smoke scripts for the `aom_nirs` package. Each example uses synthetic
NIR-like spectra (smooth Gaussian-band mixtures with baseline drift and a
sparse linear target); no real datasets are bundled. Run any of them with:

```bash
pip install -e .
python examples/01_aom_pls_quickstart.py
```

## Files

| File | Demonstrates | Paper reference |
|------|--------------|------------------|
| `01_aom_pls_quickstart.py` | `AOMPLSRegressor` with the compact bank and 5-fold CV. Prints test RMSE and the selected operator(s). | Section 3 (AOM-PLS, global selection). |
| `02_aom_ridge_blender.py`  | `AOMRidgeBlender` with the 8 HEADLINE candidate variants. Prints the convex blend weights and the dominant candidate. | Section 4 / Table 2 (best empirical result: median RMSEP ratio 0.918 vs Ridge-default, Wilcoxon Holm-corrected p = 2.6e-4). |
| `03_fastaom_quickstart.py` | `FastAOMPLSRidge(model="sparse_mkr", primitive_bank="compact")`. Prints RMSE, fit time, and screening statistics. | Section 5 (FastAOM speed champion: ratio 1.022 at ~2.5 s per fit). |
| `paper_smoke.py`           | Side-by-side comparison of `PLSRegression`, `AOMPLSRegressor`, `ASLSBaseline -> AOMPLSRegressor`, `AOMRidgeRegressor(selection="global")`, `AOMRidgeBlender`, and `FastAOMPLSRidge`. Prints a markdown-style table with RMSE, fit time, and wins vs. the PLS baseline. | Talanta manuscript Tables 1 and 2; benchmark protocol in `paper/`. |

## Expected runtime

On a modern workstation (synthetic data, no GPU):

- `01_aom_pls_quickstart.py` -- under 5 s.
- `02_aom_ridge_blender.py`  -- 15-45 s (8 candidates x 3 outer folds + refit).
- `03_fastaom_quickstart.py` -- under 10 s.
- `paper_smoke.py`           -- under 5 minutes wall clock for the full table.

## Caveats

- The paper's effect sizes were measured on a 32-NIRS-dataset cohort. A
  synthetic single-dataset smoke cannot reproduce them; it is a sanity check
  that the API still wires together end-to-end.
- The real reproduction lives in `benchmarks/` (uses cohort manifests, paired
  Wilcoxon tests, and the diagnostic CSV / dashboard pipeline).
- All examples are deterministic at `random_state=0`.
