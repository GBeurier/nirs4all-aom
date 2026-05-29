#!/usr/bin/env python
"""ANALYSIS B2 -- source-family clustered sensitivity for the AOM Talanta paper.

Concern addressed
-----------------
The paper's headline paired tests pair at the *dataset* level over the strict
N=32 regression intersection. But those 32 datasets are not independent: they
share a source database / family (e.g. GRAPEVINE_LeafTraits contributes 6
datasets, DarkResp 4, COLZA/DIESEL/BERRY 3 each ...). Treating 32 correlated
rows as 32 independent observations can overstate significance. This script
re-runs the main paired comparisons at the *source-family* level (one median
ratio per family) and compares dataset-level vs family-level conclusions.

It performs NO model fits -- it only aggregates the result CSVs already on disk
and joins them to the cohort manifest's ``source_family`` column.

Method (mirrors paper/review/aggregate_stats.py exactly)
--------------------------------------------------------
1. Load the same 12 workspace CSVs, map to a unified long frame keyed by
   (dataset, variant, seed), filter status to {ok, success, completed, ""/NaN}.
2. Restrict the regression rows to the strict N=32 intersection (the paper's
   headline denominator) -- reproduced as a sanity check against final_stats.md.
3. For each comparison, average RMSEP across seeds per dataset, form the
   per-dataset ratio candidate/reference (dataset-level effect; lower is better).
4. Attach ``source_family`` (cohort_manifest.csv), collapse per-dataset ratios
   to per-family MEDIAN ratios, and re-run a one-sided sign test (binomial on
   families with median ratio < 1 = AOM win) and a one-sided Wilcoxon signed-rank
   test on the family-level log-ratios. A cluster bootstrap (resampling FAMILIES,
   not datasets) gives a 95% CI on the family-level median ratio.
5. Report dataset-level vs family-level side by side.

Inputs (all read by absolute path)
-----------------------------------
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/scenarios/paper_aom_aompls_seeds012/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/pls/paper_aom_aompls_da_seeds012/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/ridge/paper_aom_aomridge_seeds012/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/ridge/paper_aom_aomridge_cls_seeds012/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/ridge/all54_headline/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv
- /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv
- /home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv  (dataset -> source_family map)

Outputs
-------
- stdout: dataset-level vs family-level table for every comparison.
- /home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_source_family.tex
  (bare booktabs tabularx fragment, no float / caption).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Absolute paths
# ---------------------------------------------------------------------------
RUNS = Path("/home/delete/nirs4all/nirs4all-aom/benchmarks/runs")
COHORT_MANIFEST = Path("/home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv")
TABLE_OUT = Path(
    "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_source_family.tex"
)

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42
OK_STATUS = {"ok", "success", "completed", ""}

# (name, relative_path, schema)
WORKSPACES: list[tuple[str, str, str]] = [
    ("aom_pls_seeds012", "scenarios/paper_aom_aompls_seeds012/results.csv", "aom_v0_wide"),
    ("aom_pls_da_seeds012", "pls/paper_aom_aompls_da_seeds012/results.csv", "aom_v0_wide"),
    ("aom_ridge_top5_seeds012", "ridge/paper_aom_aomridge_seeds012/results.csv", "harness"),
    ("aom_ridge_cls_seeds012", "ridge/paper_aom_aomridge_cls_seeds012/results.csv", "harness"),
    ("aom_ridge_headline", "ridge/all54_headline/results.csv", "harness"),
    ("linear_default_cv5", "scenarios/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv", "linear_hpo"),
    ("pls_hpo_seed0", "scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed0/results.csv", "linear_hpo"),
    ("pls_hpo_seed1", "scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed1/results.csv", "linear_hpo"),
    ("pls_hpo_seed2", "scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed2/results.csv", "linear_hpo"),
    ("ridge_hpo_seed0", "scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed0/results.csv", "linear_hpo"),
    ("ridge_hpo_seed1", "scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed1/results.csv", "linear_hpo"),
    ("ridge_hpo_seed2", "scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed2/results.csv", "linear_hpo"),
]

# The paper's headline regression cohort excludes QUARTZ.
EXCLUDED_DATASETS = {"Quartz_spxy70"}

# The 8 pre-registered variants whose mutual OK-dataset intersection defines the
# strict N=32 headline cohort (mirrors paper_data.PAPER_VARIANT_SPECS).
STRICT_INTERSECTION_VARIANTS: list[str] = [
    "pls-default-cv5",
    "ridge-default-cv5",
    "pls-tabpfn-hpo-25trials",
    "ridge-tabpfn-hpo-60trials",
    "ASLS-AOM-compact-cv5-numpy",
    "AOM-compact-cv5-numpy",
    "AOMRidge-global-compact-none",
    "AOMRidge-Blender-headline-spxy3",
]
# Variants that require all 3 seeds 0/1/2 present to count as OK (per paper_data).
REQUIRE_3_SEEDS = {
    "pls-tabpfn-hpo-25trials",
    "ridge-tabpfn-hpo-60trials",
    "ASLS-AOM-compact-cv5-numpy",
    "AOM-compact-cv5-numpy",
}

# The B2 comparisons (label, candidate, reference). All lower-is-better RMSEP.
COMPARISONS: list[tuple[str, str, str]] = [
    ("AOMRidge-global-compact-none vs Ridge-default", "AOMRidge-global-compact-none", "ridge-default-cv5"),
    ("AOMRidge-Blender vs Ridge-default", "AOMRidge-Blender-headline-spxy3", "ridge-default-cv5"),
    ("AOM-compact-cv5 vs PLS-default", "AOM-compact-cv5-numpy", "pls-default-cv5"),
    ("ASLS-AOM-compact-cv5 vs PLS-default", "ASLS-AOM-compact-cv5-numpy", "pls-default-cv5"),
    ("AOMRidge-Blender vs Ridge-HPO", "AOMRidge-Blender-headline-spxy3", "ridge-tabpfn-hpo-60trials"),
]


# ---------------------------------------------------------------------------
# Loading (unified long frame keyed by dataset, variant, seed)
# ---------------------------------------------------------------------------
def _dataset_id(series: pd.Series) -> pd.Series:
    """Strip a leading FAMILY/ prefix and surrounding whitespace from dataset ids."""
    return series.astype("string").str.split("/").str[-1].str.strip()


def _load_workspace(name: str, path: Path, schema: str) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame()
    if schema == "aom_v0_wide":
        out["dataset"] = _dataset_id(raw["dataset"])
        out["variant"] = raw["aom_variant"] if "aom_variant" in raw.columns else np.nan
        out["seed"] = pd.to_numeric(raw.get("seed", np.nan), errors="coerce")
        out["status"] = raw.get("status", np.nan)
        out["rmsep"] = pd.to_numeric(raw.get("RMSEP", np.nan), errors="coerce")
        out["task"] = raw.get("task", "regression")
    elif schema == "harness":
        out["dataset"] = _dataset_id(raw["dataset"])
        out["variant"] = raw["canonical_name"] if "canonical_name" in raw.columns else raw.get("variant", np.nan)
        if "variant" in raw.columns and ("canonical_name" not in raw.columns):
            out["variant"] = raw["variant"]
        seed_col = "seed" if "seed" in raw.columns else ("random_state" if "random_state" in raw.columns else None)
        out["seed"] = pd.to_numeric(raw[seed_col], errors="coerce") if seed_col else np.nan
        out["status"] = raw.get("status", np.nan)
        out["rmsep"] = pd.to_numeric(raw.get("rmsep", np.nan), errors="coerce")
        out["task"] = raw.get("task", "regression")
    elif schema == "linear_hpo":
        out["dataset"] = _dataset_id(raw["dataset"])
        out["variant"] = raw.get("variant", np.nan)
        out["seed"] = pd.to_numeric(raw.get("seed", np.nan), errors="coerce")
        out["status"] = raw.get("status", np.nan)
        out["rmsep"] = pd.to_numeric(raw.get("rmsep", np.nan), errors="coerce")
        out["task"] = raw.get("task", "regression")
    else:  # pragma: no cover
        raise ValueError(schema)
    out["source_run"] = name
    for col in ("dataset", "variant", "task", "status"):
        out[col] = out[col].astype("string").str.strip()
    return out


def load_all() -> pd.DataFrame:
    frames = [_load_workspace(name, RUNS / rel, schema) for name, rel, schema in WORKSPACES]
    return pd.concat(frames, ignore_index=True)


def _ok_mask(status: pd.Series) -> pd.Series:
    s = status.astype("string").str.lower()
    return s.isna() | s.isin(OK_STATUS)


# ---------------------------------------------------------------------------
# Strict N=32 intersection (mirrors paper_data.strict_intersection)
# ---------------------------------------------------------------------------
def strict_intersection(df: pd.DataFrame) -> list[str]:
    reg = df[df["task"].astype("string").str.lower() == "regression"]
    ok_sets: list[set[str]] = []
    for variant in STRICT_INTERSECTION_VARIANTS:
        sub = reg[reg["variant"].astype("string").str.lower() == variant.lower()]
        sub = sub[_ok_mask(sub["status"])]
        if variant in REQUIRE_3_SEEDS:
            # need >=3 distinct ok seeds for the dataset to count.
            seed_counts = sub.groupby("dataset")["seed"].nunique()
            ok_ds = set(seed_counts[seed_counts >= 3].index)
        else:
            ok_ds = set(sub["dataset"].dropna().unique())
        ok_sets.append(ok_ds)
    keep = set.intersection(*ok_sets) if ok_sets else set()
    keep -= EXCLUDED_DATASETS
    return sorted(keep)


# ---------------------------------------------------------------------------
# Per-dataset ratios + family collapse
# ---------------------------------------------------------------------------
def _per_dataset_seed_mean(df: pd.DataFrame, variant: str) -> pd.Series:
    vsub = df[
        (df["variant"].astype("string").str.lower() == variant.lower())
        & (df["task"].astype("string").str.lower() == "regression")
    ]
    vsub = vsub[_ok_mask(vsub["status"])]
    if vsub.empty:
        return pd.Series(dtype=float, name=variant)
    return vsub.groupby("dataset")["rmsep"].mean().rename(variant)


def per_dataset_ratios(
    df: pd.DataFrame, candidate: str, reference: str, cohort: set[str]
) -> pd.DataFrame:
    cand = _per_dataset_seed_mean(df, candidate)
    ref = _per_dataset_seed_mean(df, reference)
    common = sorted((set(cand.index) & set(ref.index)) & cohort)
    rows = []
    for ds in common:
        cv, rv = float(cand.loc[ds]), float(ref.loc[ds])
        if not (np.isfinite(cv) and np.isfinite(rv)) or rv == 0:
            continue
        rows.append({"dataset": ds, "candidate_value": cv, "reference_value": rv, "ratio": cv / rv})
    return pd.DataFrame(rows)


def _bootstrap_median_ci(values: np.ndarray, seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(BOOTSTRAP_N, len(values)))
    medians = np.median(values[idx], axis=1)
    return float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))


def _cluster_bootstrap_family_median_ci(
    fam_medians: np.ndarray, seed: int = BOOTSTRAP_SEED
) -> tuple[float, float]:
    """95% CI on the family-level median ratio, resampling FAMILIES (clusters).

    Each bootstrap replicate draws ``n_families`` families with replacement and
    takes the median of their per-family median ratios. This is the cluster-
    bootstrap analogue of the dataset-level percentile bootstrap, treating the
    source family (not the dataset) as the resampling unit.
    """
    n = len(fam_medians)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(BOOTSTRAP_N, n))
    medians = np.median(fam_medians[idx], axis=1)
    return float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))


def analyse(df: pd.DataFrame, ds2fam: dict[str, str], cohort: set[str]) -> list[dict]:
    results = []
    for label, cand, ref in COMPARISONS:
        pdr = per_dataset_ratios(df, cand, ref, cohort)
        pdr["source_family"] = pdr["dataset"].map(ds2fam)
        unmapped = pdr[pdr["source_family"].isna()]["dataset"].tolist()

        # --- dataset level ---
        ratios = pdr["ratio"].to_numpy(dtype=float)
        n_ds = len(ratios)
        ds_median = float(np.median(ratios))
        ds_ci = _bootstrap_median_ci(ratios)
        ds_wins = int(np.sum(pdr["candidate_value"].to_numpy() < pdr["reference_value"].to_numpy()))
        ds_losses = int(np.sum(pdr["candidate_value"].to_numpy() > pdr["reference_value"].to_numpy()))
        # one-sided sign test: AOM (candidate) better than reference (ratio < 1).
        sig = ds_wins + ds_losses
        ds_sign_p = (
            float(stats.binomtest(ds_wins, sig, p=0.5, alternative="greater").pvalue)
            if sig > 0
            else float("nan")
        )

        # --- family level ---
        fam_med = pdr.groupby("source_family")["ratio"].median()
        fam_medians = fam_med.to_numpy(dtype=float)
        n_fam = len(fam_medians)
        fam_median = float(np.median(fam_medians))
        fam_ci = _cluster_bootstrap_family_median_ci(fam_medians)
        fam_wins = int(np.sum(fam_medians < 1.0))
        fam_losses = int(np.sum(fam_medians > 1.0))
        fam_ties = int(np.sum(fam_medians == 1.0))
        fam_sig = fam_wins + fam_losses
        fam_sign_p = (
            float(stats.binomtest(fam_wins, fam_sig, p=0.5, alternative="greater").pvalue)
            if fam_sig > 0
            else float("nan")
        )
        # one-sided Wilcoxon signed-rank on family-level log-ratios (median < 0 => AOM better).
        log_fam = np.log(fam_medians[fam_medians > 0])
        if log_fam.size >= 1 and np.any(log_fam != 0):
            try:
                fam_wilcoxon_p = float(
                    stats.wilcoxon(log_fam, alternative="less", zero_method="wilcox").pvalue
                )
            except ValueError:
                fam_wilcoxon_p = float("nan")
        else:
            fam_wilcoxon_p = float("nan")

        results.append(
            {
                "label": label,
                "candidate": cand,
                "reference": ref,
                "unmapped": unmapped,
                "n_datasets": n_ds,
                "ds_median": ds_median,
                "ds_ci": ds_ci,
                "ds_wins": ds_wins,
                "ds_losses": ds_losses,
                "ds_sign_p_onesided": ds_sign_p,
                "n_families": n_fam,
                "fam_median": fam_median,
                "fam_ci": fam_ci,
                "fam_wins": fam_wins,
                "fam_losses": fam_losses,
                "fam_ties": fam_ties,
                "fam_sign_p_onesided": fam_sign_p,
                "fam_wilcoxon_p_onesided": fam_wilcoxon_p,
                "fam_medians": fam_med.to_dict(),
            }
        )
    return results


# ---------------------------------------------------------------------------
# LaTeX (bare booktabs fragment)
# ---------------------------------------------------------------------------
def _esc(text: str) -> str:
    # Insert \allowbreak after hyphens in long variant labels, matching the
    # existing table_paired_stats.tex style, and escape LaTeX specials.
    text = text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
    return text.replace("-", r"-\allowbreak{}")


def _fmt_p(p: float) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    if p < 1e-3:
        mant, exp = f"{p:.1e}".split("e")
        return rf"${mant}\times10^{{{int(exp)}}}$"
    return f"{p:.3f}"


def write_table(results: list[dict], path: Path) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrrl}",
        r"\toprule",
        r" & \multicolumn{2}{c}{Cohort} & "
        r"\multicolumn{2}{c}{Median RMSEP ratio} & Family-level \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Comparison & Datasets & Families & Dataset-level & "
        r"Family-level (95\% CI) & wins / sign $p$ \\",
        r"\midrule",
    ]
    for r in results:
        fam_ci = f"{r['fam_ci'][0]:.3f}--{r['fam_ci'][1]:.3f}"
        wins = f"{r['fam_wins']}/{r['n_families']}, $p={_fmt_p(r['fam_sign_p_onesided']).strip('$')}$"
        lines.append(
            f"{_esc(r['label'])} & {r['n_datasets']} & {r['n_families']} & "
            f"{r['ds_median']:.3f} & {r['fam_median']:.3f} ({fam_ci}) & {wins} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    df = load_all()

    cohort = set(strict_intersection(df))
    print(f"Strict regression intersection N = {len(cohort)} datasets.")

    man = pd.read_csv(COHORT_MANIFEST)
    man = man[man["task"].astype("string").str.lower() == "regression"].copy()
    man["ds_id"] = _dataset_id(man["dataset"])
    ds2fam = dict(zip(man["ds_id"], man["source_family"].astype("string")))

    fam_in_cohort = sorted({ds2fam[d] for d in cohort if d in ds2fam})
    print(f"Cohort collapses to {len(fam_in_cohort)} source families.")
    counts = pd.Series([ds2fam[d] for d in cohort if d in ds2fam]).value_counts()
    print("Family sizes:", dict(counts))
    print()

    results = analyse(df, ds2fam, cohort)

    hdr = (
        f"{'Comparison':<48} {'N_ds':>5} {'N_fam':>6} {'ds_med':>7} "
        f"{'ds_p1':>8} {'fam_med':>8} {'fam_CI':>16} {'fam_wins':>9} {'fam_p1':>8} {'fam_wilc':>9}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        if r["unmapped"]:
            print(f"  WARNING unmapped datasets in {r['label']}: {r['unmapped']}")
        ci = f"{r['fam_ci'][0]:.3f}-{r['fam_ci'][1]:.3f}"
        print(
            f"{r['label']:<48} {r['n_datasets']:>5d} {r['n_families']:>6d} "
            f"{r['ds_median']:>7.3f} {r['ds_sign_p_onesided']:>8.3f} "
            f"{r['fam_median']:>8.3f} {ci:>16} "
            f"{r['fam_wins']:>3d}/{r['n_families']:<3d}  "
            f"{r['fam_sign_p_onesided']:>8.3f} {r['fam_wilcoxon_p_onesided']:>9.3f}"
        )
    print()
    print("Dataset-level 95% CI (percentile bootstrap over datasets):")
    for r in results:
        print(
            f"  {r['label']:<48} ratio={r['ds_median']:.3f} "
            f"CI={r['ds_ci'][0]:.3f}-{r['ds_ci'][1]:.3f} wins={r['ds_wins']}/{r['n_datasets']}"
        )
    print()
    print("Per-family median ratios:")
    for r in results:
        print(f"  {r['label']}:")
        for fam, v in sorted(r["fam_medians"].items(), key=lambda kv: kv[1]):
            print(f"      {fam:<24} {v:.4f}")

    write_table(results, TABLE_OUT)
    print(f"\nWrote LaTeX fragment: {TABLE_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
