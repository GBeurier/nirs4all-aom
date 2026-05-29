# Reproducing the AOM / Talanta 2026 paper

This repository (`nirs4all-aom`, <https://github.com/GBeurier/nirs4all-aom>) is the **reference
implementation and reproduction support** for the paper *"Folding linear preprocessing selection into
the calibration model: operator-adaptive PLS and Ridge for near-infrared spectroscopy"* (Talanta,
in preparation; arXiv:2605.13587 preprint of the earlier version).

> The Python package `aom_nirs` is the **reference implementation** used for every number in the
> paper. The same numerical methods are *additionally* provided as a portable C\#++ implementation
> with multi-language bindings in **`nirs4all-methods`** (and its `pls4all` subset); that C++ engine
> is validated against this Python reference to machine precision and is the long-term portable home.
> `\rc{}` *The C++/multi-language release is forthcoming — pin its version/commit here at submission.*

## Layout

```
aom_nirs/                     reference implementation: pls/ (AOM-PLS, POP-PLS, DA),
                              ridge/ (AOM-Ridge family), fast/ (FastAOM chains)
benchmarks/
  runs/                       committed result CSVs (variant × dataset × seed × metric)
    scenarios/paper_aom_*     AOM-PLS, FastAOM, linear-HPO cartesian baselines
    ridge/                    AOM-Ridge regression + classification + all54_headline
    pls/                      AOM-PLS-DA
_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv   frozen master (all axes)
paper/
  review/                    aggregate_stats.py, build_paper_figures.py, cohort_manifest.csv,
                             final_stats.md (numbers source of truth)
  repro/                     the 5 robustness/coverage/deployment aggregations (see repro/README.md)
  figures/  tables/          paper figures + LaTeX table fragments
docs/  tests/                math notes, architecture, unit tests (incl. the identity invariants)
```

The manuscript itself (LaTeX) lives in the sibling paper project
`nirs4all-papers/aom_talanta_26/manuscript/` and `\input`s the figures/tables produced here.

## Steps

1. **Install** (Python ≥3.11): `pip install -e .[bench]` (numpy, scipy, scikit-learn, joblib,
   pandas, pybaselines, matplotlib, pyarrow).
2. **Validate the methods** — unit tests pin the algebraic identities
   (`(XAᵀ)ᵀY = AXᵀY`, NIPALS-adjoint == covariance, original-grid coefficients, the Ridge kernel):
   `pytest tests/pls/test_estimators.py tests/ridge/test_blender.py -q`.
3. **5-minute smoke** on synthetic spectra: `python examples/paper_smoke.py`.
4. **Regenerate the paper tables/figures from the committed CSVs (no refitting):**
   - headline regression/runtime/classification tables + figures: `python paper/review/build_paper_figures.py`
   - robustness / coverage / deployment aggregations (source-family clustering, HPO recipe & union,
     transfer + latency, seed/determinism): `paper/repro/run_all.sh` (see `paper/repro/README.md`).
   Each aggregation reproduces a known `paper/review/final_stats.md` value as a sanity check.
5. **Build the manuscript:** in `nirs4all-papers/aom_talanta_26/manuscript/`, run `bash build.sh`
   (article-class drafts `main`/`supplement` + Elsevier `main_elsarticle`/`supplement_elsarticle`).
6. **Re-run a fresh benchmark** (multi-hour; needs the NIR datasets, not redistributed here):
   `python benchmarks/<family>/run_*.py --cohort benchmarks/<family>/cohort_*.csv`.

## Scope of the paper

PLS / Ridge / FastAOM (PLS→Ridge) and their AOM variants only. Neural / foundation-model methods
(TabPFN, CNN/NICON, CatBoost), mixture-of-experts and the multi-kernel arm are **not** comparators in
this paper (TabPFN appears only as the proposal engine inside the HPO baseline, not as a model).

## Citation

See `CITATION.cff`. Cite `nirs4all-aom` for the methods/benchmark; cite `nirs4all` only for the NIRS
instrumentation/provenance context of the local datasets.
