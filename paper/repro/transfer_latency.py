#!/usr/bin/env python3
"""Transfer (leave-site-out) generalization + inference-latency aggregation for the AOM Talanta paper.

PURE AGGREGATION over existing on-disk benchmark results. NO model fitting.

What it does
------------
(A) TRANSFER table: on the leave-site-out Rd25 datasets (split_type=external_site_*)
    Rd25_CBtestSite / Rd25_GTtestSite / Rd25_XSBNtestSite, contrasted with the paired
    RANDOM control Rd25_spxy70 (split_type=spxy70, same domain_group=leaf-physiology,
    same source_family=DarkResp). For each of five model families
    (AOM-PLS, AOM-Ridge, PLS, Ridge, CNN(NICON)) it reports the per-dataset median RMSEP
    aggregated across available model seeds, the median RMSEP across the three blocked
    sites, and the GENERALIZATION GAP = (median blocked-site RMSEP) / (random-split RMSEP)
    -- a ratio > 1 means the model degrades under a true site transfer relative to the
    random split. Also reports the additive gap (blocked - random).

(B) LATENCY table: median predict_time_s and median fit_time_s (in seconds) by model
    family on these four datasets, supporting the deployability/latency claim
    (a linear AOM model predicts orders of magnitude faster than a CNN).

Representative estimator per family (the paper's "simple/headline" variant, consistent
with paper/review/final_stats.md and the manuscript main-results table):
    AOM-PLS    -> AOM-compact-cv5-numpy            (seeds 0,1,2)
    AOM-Ridge  -> AOMRidge-global-compact-none     (seed 0; estimator is deterministic)
    PLS        -> PLS-standard-numpy               (seeds 0,1,2)
    Ridge      -> Ridge-raw                         (seeds 0,1,2)
    CNN(NICON) -> V2L-baseline                      (nicon_v2 CNN reference, seeds 0-4,
                                                     full fit/predict timing)

Aggregation rule: the master CSV pools several source-run campaigns, so a given
(dataset, variant, seed) cell can appear more than once (bit-identical for the
deterministic estimators; genuinely distinct campaign re-runs for PLS-standard /
Ridge-raw). We therefore first collapse to ONE value per (dataset, seed) by mean
(matching paper/review/aggregate_stats.py's per-dataset-seed-mean reduction), then take
the median across seeds. Tleaf_grp70_30 and FinalScore_grp70_30_scoreQ are NOT used
(empty/sparse rmsep).

Inputs (absolute paths)
-----------------------
  /home/delete/nirs4all/nirs4all-aom/_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv
  /home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv
  /home/delete/nirs4all/nirs4all-aom/benchmarks/runs/ridge/all54_headline/results.csv   (sanity cross-check only)

Outputs (absolute paths)
------------------------
  /home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_transfer.tex
  /home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_latency.tex
  (plus printed numbers to stdout)
"""

from __future__ import annotations

import pandas as pd

MASTER = "/home/delete/nirs4all/nirs4all-aom/_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv"
COHORT = "/home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv"
HEADLINE = "/home/delete/nirs4all/nirs4all-aom/benchmarks/runs/ridge/all54_headline/results.csv"

TABLE_TRANSFER = "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_transfer.tex"
TABLE_LATENCY = "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_latency.tex"

BLOCKED = ["Rd25_CBtestSite", "Rd25_GTtestSite", "Rd25_XSBNtestSite"]
RANDOM = "Rd25_spxy70"
DATASETS = BLOCKED + [RANDOM]

# display label -> (model_class, variant) representative estimator
FAMILIES = [
    ("AOM-PLS", ("AOM-PLS", "AOM-compact-cv5-numpy")),
    ("AOM-Ridge", ("AOM-Ridge", "AOMRidge-global-compact-none")),
    ("PLS", ("PLS", "PLS-standard-numpy")),
    ("Ridge", ("Ridge", "Ridge-raw")),
]
# short site labels for the transfer table header
SITE_LABEL = {"Rd25_CBtestSite": "CB", "Rd25_GTtestSite": "GT", "Rd25_XSBNtestSite": "XSBN"}


def load_cells(df: pd.DataFrame, model_class: str, variant: str) -> pd.DataFrame:
    """One value per (dataset, seed) for the given estimator: mean across pooled source-run copies."""
    s = df[(df["model_class"] == model_class) & (df["variant"] == variant) & df["dataset"].isin(DATASETS)].copy()
    cell = (
        s.groupby(["dataset", "seed"], dropna=False)
        .agg(rmsep=("rmsep", "mean"), fit_time_s=("fit_time_s", "mean"), predict_time_s=("predict_time_s", "mean"))
        .reset_index()
    )
    return cell


def per_dataset_median(cell: pd.DataFrame, col: str) -> dict[str, float]:
    """Median over seeds per dataset for one column (NaNs dropped)."""
    g = cell.dropna(subset=[col]).groupby("dataset")[col].median()
    return {d: float(g[d]) for d in g.index}


def sanity_check(df: pd.DataFrame) -> tuple[bool, str]:
    """Cross-check AOMRidge-global-compact-none RMSEP in the master against the canonical
    all54_headline run CSV for the four Rd25 datasets. Proves the load/join is correct."""
    h = pd.read_csv(HEADLINE, low_memory=False)
    ok = True
    lines = []
    for d in DATASETS:
        hv = h[(h["dataset"] == d) & (h["variant"] == "AOMRidge-global-compact-none")]["rmsep"]
        mv = df[(df["dataset"] == d) & (df["variant"] == "AOMRidge-global-compact-none")
                & (df["model_class"] == "AOM-Ridge")]["rmsep"].dropna().unique()
        href = float(hv.iloc[0])
        match = len(mv) == 1 and abs(float(mv[0]) - href) < 1e-9
        ok = ok and match
        lines.append(f"  {d}: headline_csv={href:.6f}  master={float(mv[0]):.6f}  match={match}")
    return ok, "\n".join(lines)


def fmt(x: float, nd: int = 4) -> str:
    return f"{x:.{nd}f}"


def main() -> None:
    df = pd.read_csv(MASTER, low_memory=False)
    coh = pd.read_csv(COHORT)

    # ----- sanity -----
    ok, sc = sanity_check(df)
    print("=== SANITY CHECK: AOMRidge-global-compact-none RMSEP, master vs all54_headline run CSV ===")
    print(sc)
    print(f"  ALL MATCH = {ok}\n")

    cm = coh[coh["dataset"].isin(DATASETS)].set_index("dataset")
    print("=== Cohort pairing (cohort_manifest.csv) ===")
    for d in DATASETS:
        print(f"  {d:20s} split_type={cm.loc[d,'split_type']:18s} "
              f"domain={cm.loc[d,'domain_group']} source_family={cm.loc[d,'source_family']} "
              f"n_train={int(cm.loc[d,'n_train'])} n_test={int(cm.loc[d,'n_test'])}")
    print()

    # ----- (A) TRANSFER -----
    transfer_rows = []
    print("=== (A) TRANSFER: median RMSEP across seeds, per dataset ===")
    for label, (mc, var) in FAMILIES:
        cell = load_cells(df, mc, var)
        med = per_dataset_median(cell, "rmsep")
        seeds = sorted(cell["seed"].dropna().unique().tolist())
        blocked_vals = [med[d] for d in BLOCKED if d in med]
        blocked_median = float(pd.Series(blocked_vals).median())
        rand = med.get(RANDOM, float("nan"))
        gap_ratio = blocked_median / rand
        gap_abs = blocked_median - rand
        transfer_rows.append({
            "label": label, "variant": var, "seeds": seeds,
            **{SITE_LABEL[d]: med.get(d, float("nan")) for d in BLOCKED},
            "blocked_median": blocked_median, "random": rand,
            "gap_ratio": gap_ratio, "gap_abs": gap_abs,
        })
        print(f"  {label:12s} ({var}) seeds={seeds}")
        for d in BLOCKED:
            print(f"       {SITE_LABEL[d]:5s} (blocked) RMSEP={med.get(d, float('nan')):.4f}")
        print(f"       blocked-median={blocked_median:.4f}  random({RANDOM})={rand:.4f}  "
              f"gap_ratio={gap_ratio:.3f}  gap_abs={gap_abs:+.4f}")
    print()

    # ----- (B) LATENCY -----
    latency_rows = []
    print("=== (B) LATENCY: median predict/fit time (s) over the 4 Rd25 datasets ===")
    for label, (mc, var) in FAMILIES:
        cell = load_cells(df, mc, var)
        # median over all (dataset, seed) cells across the 4 datasets
        med_pred = float(cell["predict_time_s"].median())
        med_fit = float(cell["fit_time_s"].median())
        n_pred = int(cell["predict_time_s"].notna().sum())
        n_fit = int(cell["fit_time_s"].notna().sum())
        latency_rows.append({"label": label, "variant": var,
                             "median_predict_s": med_pred, "median_fit_s": med_fit,
                             "n_pred": n_pred, "n_fit": n_fit})
        print(f"  {label:12s} median_predict_s={med_pred:.4f} (n={n_pred})  "
              f"median_fit_s={med_fit:.4f} (n={n_fit})")
    print()

    # ----- write TRANSFER fragment -----
    tr = []
    tr.append(r"\begin{tabularx}{\linewidth}{Xrrrrrr}")
    tr.append(r"\toprule")
    tr.append(r"Model & CB & GT & XSBN & Blocked & Random & Gap \\")
    tr.append(r" & (site) & (site) & (site) & median & (\texttt{spxy70}) & ratio \\")
    tr.append(r"\midrule")
    for r in transfer_rows:
        tr.append(
            f"{r['label']} & {fmt(r['CB'])} & {fmt(r['GT'])} & {fmt(r['XSBN'])} & "
            f"{fmt(r['blocked_median'])} & {fmt(r['random'])} & {fmt(r['gap_ratio'], 3)} \\\\"
        )
    tr.append(r"\bottomrule")
    tr.append(r"\end{tabularx}")
    with open(TABLE_TRANSFER, "w") as f:
        f.write("\n".join(tr) + "\n")

    # ----- write LATENCY fragment -----
    la = []
    la.append(r"\begin{tabularx}{\linewidth}{Xrr}")
    la.append(r"\toprule")
    la.append(r"Model & Median predict (s) & Median fit (s) \\")
    la.append(r"\midrule")
    for r in latency_rows:
        la.append(f"{r['label']} & {fmt(r['median_predict_s'])} & {fmt(r['median_fit_s'])} \\\\")
    la.append(r"\bottomrule")
    la.append(r"\end{tabularx}")
    with open(TABLE_LATENCY, "w") as f:
        f.write("\n".join(la) + "\n")

    print(f"Wrote {TABLE_TRANSFER}")
    print(f"Wrote {TABLE_LATENCY}")


if __name__ == "__main__":
    main()
