#!/usr/bin/env python3
"""Seed-stability / Ridge-determinism aggregation for the AOM Talanta paper (Analysis A1).

This is a PURE AGGREGATION over result CSVs already on disk. No model is fit here.

It quantifies how each linear-model variant's held-out test error responds to the
random seed across seeds 0/1/2. For every (variant, dataset) cell it computes the
mean and standard deviation of the metric across the available seeds, then summarises
per variant: the median (and max) of the per-dataset across-seed std, and the fraction
of datasets that show ANY seed variation.

Key finding demonstrated by the numbers:
  * AOM-Ridge estimators are essentially DETERMINISTIC: per-(variant,dataset) RMSEP std
    is exactly 0 for every cell. Seed jitter is therefore not a meaningful robustness
    axis for Ridge. (The held-out test partition n_test is also invariant across seeds,
    confirmed in the tuned-HPO files which carry n_test.)
  * AOM-PLS DOES vary across seeds on a fraction of datasets, but only for the variants
    whose component selection uses K-fold CV (AOM-compact-cv3/cv5, ASLS-AOM-compact-cv5,
    POP-*). The non-CV PLS variants (PLS-standard, simpls-covariance, nipals-adjoint,
    nirs4all-AOM-PLS-default) are deterministic.
  * IMPORTANT SCOPE: the held-out TEST PARTITION is FIXED across these seeds. This is
    seed-of-CV stability, NOT train/test partition robustness (which is a separate,
    unaddressed axis).

The classification sources (AOM-Ridge-Cls, AOM-PLS-DA) carry no RMSEP; their primary
classification metric (balanced accuracy) is summarised the same way and is likewise
fully deterministic across seeds.

INPUTS (read by absolute path, all already on disk):
  AOM-PLS regression  : nirs4all-aom/benchmarks/runs/scenarios/paper_aom_aompls_seeds012/results.csv
  AOM-Ridge regression: nirs4all-aom/benchmarks/runs/ridge/paper_aom_aomridge_seeds012/results.csv
  AOM-Ridge classif.  : nirs4all-aom/benchmarks/runs/ridge/paper_aom_aomridge_cls_seeds012/results.csv
  AOM-PLS-DA classif. : nirs4all-aom/benchmarks/runs/pls/paper_aom_aompls_da_seeds012/results.csv
  Tuned PLS  HPO      : .../scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv
  Tuned Ridge HPO     : .../scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv

OUTPUTS:
  stdout                                  : per-variant summary + the sanity-check reproduction
  manuscript/tables/table_seed_determinism.tex : bare booktabs/tabularx fragment
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Absolute input paths
# ---------------------------------------------------------------------------
AOM_ROOT = "/home/delete/nirs4all/nirs4all-aom"
RUNS = f"{AOM_ROOT}/benchmarks/runs"
SCEN = f"{RUNS}/scenarios"

PATH_AOMPLS = f"{SCEN}/paper_aom_aompls_seeds012/results.csv"
PATH_AOMRIDGE = f"{RUNS}/ridge/paper_aom_aomridge_seeds012/results.csv"
PATH_AOMRIDGE_CLS = f"{RUNS}/ridge/paper_aom_aomridge_cls_seeds012/results.csv"
PATH_AOMPLS_DA = f"{RUNS}/pls/paper_aom_aompls_da_seeds012/results.csv"
PATH_PLS_HPO = [
    f"{SCEN}/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{s}/results.csv"
    for s in (0, 1, 2)
]
PATH_RIDGE_HPO = [
    f"{SCEN}/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{s}/results.csv"
    for s in (0, 1, 2)
]

OUT_TABLE = (
    "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/"
    "table_seed_determinism.tex"
)

# Cells are deemed "varying" if the across-seed std exceeds this floating-point floor.
ZERO_TOL = 1e-12

# ---------------------------------------------------------------------------
# Loading helpers: normalise each source to (variant, dataset, seed, metric, metric_name)
# ---------------------------------------------------------------------------


def _load_long(path, *, variant_col, dataset_col, seed_col, metric_col, metric_name,
               status_ok=True):
    """Read one results CSV and return a normalised long frame for ok rows with a finite metric."""
    df = pd.read_csv(path)
    if status_ok and "status" in df.columns:
        df = df[df["status"] == "ok"]
    out = pd.DataFrame(
        {
            "variant": df[variant_col].astype(str),
            "dataset": df[dataset_col].astype(str),
            "seed": df[seed_col].astype("Int64"),
            "metric": pd.to_numeric(df[metric_col], errors="coerce"),
        }
    )
    out = out.dropna(subset=["metric", "seed"])
    # Scope exclusion (paper presents PLS/Ridge/FastAOM only — no multi-kernel/NN):
    # drop the multi-kernel variants (MultiBranchMKL, AOMRidgeCls-mkl) so the table
    # matches the paper's scope and the committed fragment.
    _excl = out["variant"].str.contains("MultiBranchMKL|MultiKernel|-mkl-|mkl-compact", case=False, regex=True)
    out = out[~_excl]
    out["metric_name"] = metric_name
    return out


def load_sources():
    """Load every A1 source. Returns dict source_label -> (long_frame, family_label)."""
    src = {}

    # --- RMSEP-bearing regression sources -----------------------------------
    src["AOM-PLS (regression)"] = (
        _load_long(
            PATH_AOMPLS,
            variant_col="model",
            dataset_col="dataset",
            seed_col="seed",
            metric_col="RMSEP",
            metric_name="RMSEP",
        ),
        "AOM-PLS",
    )
    src["AOM-Ridge (regression)"] = (
        _load_long(
            PATH_AOMRIDGE,
            variant_col="variant",
            dataset_col="dataset",
            seed_col="random_state",
            metric_col="rmsep",
            metric_name="RMSEP",
        ),
        "AOM-Ridge",
    )

    # Tuned linear baselines (one CSV per seed) ------------------------------
    pls_hpo = pd.concat(
        [
            _load_long(p, variant_col="variant", dataset_col="dataset", seed_col="seed",
                       metric_col="rmsep", metric_name="RMSEP")
            for p in PATH_PLS_HPO
        ],
        ignore_index=True,
    )
    pls_hpo["variant"] = "PLS-HPO (25 trials)"  # scope: drop TabPFN-driver runner key from the label
    src["PLS-TabPFN-HPO (regression)"] = (pls_hpo, "Tuned PLS")

    ridge_hpo = pd.concat(
        [
            _load_long(p, variant_col="variant", dataset_col="dataset", seed_col="seed",
                       metric_col="rmsep", metric_name="RMSEP")
            for p in PATH_RIDGE_HPO
        ],
        ignore_index=True,
    )
    ridge_hpo["variant"] = "Ridge-HPO (60 trials)"  # scope: drop TabPFN-driver runner key from the label
    src["Ridge-TabPFN-HPO (regression)"] = (ridge_hpo, "Tuned Ridge")

    # --- Classification sources (no RMSEP -> balanced accuracy) -------------
    src["AOM-Ridge-Cls (classification)"] = (
        _load_long(
            PATH_AOMRIDGE_CLS,
            variant_col="variant",
            dataset_col="dataset",
            seed_col="random_state",
            metric_col="balanced_accuracy",
            metric_name="balanced accuracy",
        ),
        "AOM-Ridge-Cls",
    )
    src["AOM-PLS-DA (classification)"] = (
        _load_long(
            PATH_AOMPLS_DA,
            variant_col="model",
            dataset_col="dataset",
            seed_col="seed",
            metric_col="balanced_accuracy",
            metric_name="balanced accuracy",
        ),
        "AOM-PLS-DA",
    )
    return src


# ---------------------------------------------------------------------------
# Per-source aggregation
# ---------------------------------------------------------------------------


def summarise_source(long_df):
    """Per-source summary across all its variants.

    Population-level std (ddof=0) of the metric within each (variant, dataset)
    cell across the available seeds, then summarise across datasets.
    """
    # per (variant, dataset) cell: std across seeds (population std, ddof=0)
    cell = (
        long_df.groupby(["variant", "dataset"])["metric"]
        .agg(seed_std=lambda s: float(np.std(s.values, ddof=0)),
             n_seeds=lambda s: int(s.nunique()))
        .reset_index()
    )
    n_datasets = cell["dataset"].nunique()
    n_seeds = int(long_df["seed"].nunique())
    median_std = float(cell["seed_std"].median())
    max_std = float(cell["seed_std"].max())
    n_varying = int((cell["seed_std"] > ZERO_TOL).sum())
    n_cells = int(len(cell))
    frac_varying = n_varying / n_cells if n_cells else float("nan")
    return {
        "n_datasets": n_datasets,
        "n_cells": n_cells,
        "n_seeds": n_seeds,
        "median_seed_std": median_std,
        "max_seed_std": max_std,
        "n_varying_cells": n_varying,
        "frac_varying": frac_varying,
        "_cells": cell,
    }


def summarise_per_variant(long_df):
    """Per-variant breakdown within a source.

    For each variant: number of datasets, number of seeds, median and max of the
    per-dataset across-seed std, and the number of datasets showing ANY variation.
    """
    cell = (
        long_df.groupby(["variant", "dataset"])["metric"]
        .agg(seed_std=lambda s: float(np.std(s.values, ddof=0)))
        .reset_index()
    )
    seeds_per_variant = long_df.groupby("variant")["seed"].nunique()
    rows = []
    for v, sub in cell.groupby("variant"):
        rows.append(
            {
                "variant": v,
                "n_datasets": int(sub["dataset"].nunique()),
                "n_seeds": int(seeds_per_variant.loc[v]),
                "median_seed_std": float(sub["seed_std"].median()),
                "max_seed_std": float(sub["seed_std"].max()),
                "n_varying": int((sub["seed_std"] > ZERO_TOL).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("median_seed_std", ascending=False)


# ---------------------------------------------------------------------------
# Sanity check (validates data load + joins against a published number)
# ---------------------------------------------------------------------------


def sanity_check():
    """Reproduce table_aomridge_family.tex seeds012 median RMSEP per variant.

    Expected (from the manuscript fragment): split_aware 0.371, cv-blended 0.484,
    knn50 0.523, Ridge-raw 0.571.
    """
    df = pd.read_csv(PATH_AOMRIDGE)
    expected = {
        "AOMRidge-global-compact-none-split_aware": 0.371,
        "AOMRidge-Local-compact-cv-blended": 0.484,
        "AOMRidge-Local-compact-knn50": 0.523,
        "Ridge-raw": 0.571,
    }
    ok = True
    lines = []
    for v, exp in expected.items():
        got = round(float(df.loc[df["variant"] == v, "rmsep"].median()), 3)
        match = got == exp
        ok = ok and match
        lines.append(f"  {v}: median RMSEP got={got:.3f} expected={exp:.3f} -> {'OK' if match else 'MISMATCH'}")
    return ok, lines


# ---------------------------------------------------------------------------
# LaTeX fragment
# ---------------------------------------------------------------------------


def _fmt_std(x):
    """Format a std value for the table.

    Exact 0 prints as "0". Values below 1e-9 are floating-point round-off of an
    exactly-deterministic estimator and are rendered as a single round-off marker
    "$<$1e$-$9". Otherwise 4 decimal places.
    """
    if x == 0.0:
        return "0"
    if x < 1e-9:
        return r"$<$1e$-$9"
    return f"{x:.4f}"


def write_table(blocks, path):
    """blocks: list of (family_label, per_variant_DataFrame).

    Emits one row per variant with: variant, #datasets, #seeds, median per-dataset
    RMSEP std, max std, #datasets with variation. Family blocks are separated by a
    \\midrule. The metric is RMSEP for regression families and balanced accuracy for
    the classification families (named in the family header cell).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = []
    lines.append(r"\begin{tabularx}{\linewidth}{lXrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r"Family & Variant & \#Datasets\,/\,\#Seeds & "
        r"Median seed std & Max seed std & \#Datasets varying \\"
    )
    lines.append(r"\midrule")
    for bi, (family, df) in enumerate(blocks):
        if bi > 0:
            lines.append(r"\midrule")
        fam_tex = family.replace("-", r"-\allowbreak{}")
        for j, (_, r) in enumerate(df.iterrows()):
            fam_cell = fam_tex if j == 0 else ""
            var = str(r["variant"]).replace("-", r"-\allowbreak{}").replace("_", r"\_")
            lines.append(
                f"{fam_cell} & {var} & {r['n_datasets']}\\,/\\,{r['n_seeds']} & "
                f"{_fmt_std(r['median_seed_std'])} & {_fmt_std(r['max_seed_std'])} & "
                f"{r['n_varying']}/{r['n_datasets']} \\\\"
            )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabularx}")
    text = "\n".join(lines) + "\n"
    with open(path, "w") as fh:
        fh.write(text)
    return text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    sources = load_sources()

    # Fixed display order: regression RMSEP sources first, then classification.
    order = [
        "AOM-PLS (regression)",
        "AOM-Ridge (regression)",
        "PLS-TabPFN-HPO (regression)",
        "Ridge-TabPFN-HPO (regression)",
        "AOM-Ridge-Cls (classification)",
        "AOM-PLS-DA (classification)",
    ]

    # Family label shown in the LaTeX table (classification families flag the metric).
    family_label = {
        "AOM-PLS (regression)": "AOM-PLS",
        "AOM-Ridge (regression)": "AOM-Ridge",
        "PLS-TabPFN-HPO (regression)": "Tuned PLS",
        "Ridge-TabPFN-HPO (regression)": "Tuned Ridge",
        "AOM-Ridge-Cls (classification)": "AOM-Ridge-Cls (bal. acc.)",
        "AOM-PLS-DA (classification)": "AOM-PLS-DA (bal. acc.)",
    }

    print("=" * 78)
    print("A1 SEED STABILITY / RIDGE DETERMINISM  (pure aggregation, no fits)")
    print("=" * 78)
    blocks = []
    for label in order:
        long_df, _family = sources[label]
        s = summarise_source(long_df)
        metric_name = long_df["metric_name"].iloc[0]
        pv = summarise_per_variant(long_df)
        blocks.append((family_label[label], pv))
        print(
            f"\n{label}\n"
            f"  variants={long_df['variant'].nunique()}  datasets={s['n_datasets']}  "
            f"cells={s['n_cells']}  seeds={s['n_seeds']}  metric={metric_name}\n"
            f"  median per-(variant,dataset) seed-std = {s['median_seed_std']:.3e}\n"
            f"  max    per-(variant,dataset) seed-std = {s['max_seed_std']:.3e}\n"
            f"  (variant,dataset) cells with ANY seed variation = "
            f"{s['n_varying_cells']}/{s['n_cells']} ({100*s['frac_varying']:.1f}%)"
        )
        print("  per-variant:")
        for _, r in pv.iterrows():
            print(
                f"    {r['variant']:46s} n_ds={r['n_datasets']:>3d} seeds={r['n_seeds']} "
                f"median_std={r['median_seed_std']:.3e} max_std={r['max_seed_std']:.3e} "
                f"#varying={r['n_varying']:>3d}/{r['n_datasets']}"
            )

    # Sanity check
    print("\n" + "=" * 78)
    print("SANITY CHECK: reproduce table_aomridge_family.tex seeds012 median RMSEP")
    print("=" * 78)
    ok, lines = sanity_check()
    for ln in lines:
        print(ln)
    print(f"  => sanity check {'PASSED' if ok else 'FAILED'}")

    # Write the LaTeX fragment
    text = write_table(blocks, OUT_TABLE)
    print("\n" + "=" * 78)
    print(f"Wrote LaTeX fragment: {OUT_TABLE}")
    print("=" * 78)
    print(text)


if __name__ == "__main__":
    main()
