#!/usr/bin/env python3
"""B4 — classification probability calibration (log-loss + ECE) alongside balanced accuracy.

Pure aggregation over the committed classification result CSVs (no model fitting):
  - pls/paper_aom_aompls_da_seeds012/results.csv      (PLS-DA / AOM-PLS-DA / POP-PLS-DA)
  - ridge/paper_aom_aomridge_cls_seeds012/results.csv (AOMRidgeCls family)
Reports per-variant median balanced accuracy, log-loss and ECE across (dataset, seed).
Scope: drops the multi-kernel `mkl` Ridge-classifier variant. Writes a LaTeX fragment.
"""
from pathlib import Path
import pandas as pd

RUNS = Path("/home/delete/nirs4all/nirs4all-aom/benchmarks/runs")
OUT = Path("/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_classification_calib.tex")
DA = RUNS / "pls/paper_aom_aompls_da_seeds012/results.csv"
CLS = RUNS / "ridge/paper_aom_aomridge_cls_seeds012/results.csv"

def load(path, vcol):
    d = pd.read_csv(path)
    if "status" in d.columns:
        d = d[d["status"] == "ok"]
    d = d.rename(columns={vcol: "variant"})
    for m in ("balanced_accuracy", "log_loss", "ece"):
        d[m] = pd.to_numeric(d[m], errors="coerce")
    return d[["variant", "dataset", "balanced_accuracy", "log_loss", "ece"]]

da = load(DA, "model")
cls = load(CLS, "variant")
cls = cls[~cls["variant"].str.contains("mkl", case=False)]  # scope: no multi-kernel

def summary(d):
    g = d.groupby("variant").agg(
        n_obs=("balanced_accuracy", "size"),
        bal_acc=("balanced_accuracy", "median"),
        log_loss=("log_loss", "median"),
        ece=("ece", "median"),
    ).reset_index()
    return g

sda, scls = summary(da), summary(cls)
print("=== PLS-DA / AOM-PLS-DA ==="); print(sda.to_string(index=False))
print("=== AOM-Ridge-Cls (mkl dropped) ==="); print(scls.to_string(index=False))

# sanity: balanced-accuracy delta of the headline DA variant vs PLS-DA-standard (paper: +0.159, N=13 paired)
base = da[da["variant"] == "PLS-DA-standard"].set_index("dataset")["balanced_accuracy"]
head = da[da["variant"] == "AOM-PLS-DA-global-simpls-covariance"].set_index("dataset")["balanced_accuracy"]
common = base.index.intersection(head.index)
delta = (head.loc[common] - base.loc[common]).median()
print(f"\nSANITY: median Δ balanced acc (AOM-PLS-DA-global-simpls-cov − PLS-DA), N={len(common)} = {delta:.3f}  (paper +0.159)")

def row(v, label):
    r = pd.concat([sda, scls]).set_index("variant").loc[v]
    return rf"{label} & {r.bal_acc:.3f} & {r.log_loss:.3f} & {r.ece:.3f} \\"

esc = lambda s: s.replace("-", r"-\allowbreak{}")
lines = [
    r"\begin{tabularx}{\linewidth}{Xrrr}", r"\toprule",
    r"Variant & Median bal.\ acc. & Median log-loss & Median ECE \\", r"\midrule",
    row("PLS-DA-standard", esc("PLS-DA-standard")),
    row("AOM-PLS-DA-global-simpls-covariance", esc("AOM-PLS-DA-global-simpls-covariance")),
    row("AOM-PLS-DA-global-nipals-adjoint", esc("AOM-PLS-DA-global-nipals-adjoint")),
    r"\midrule",
    row("AOMRidgeCls-global-compact", esc("AOMRidgeCls-global-compact")),
    row("AOMRidgeCls-superblock-compact", esc("AOMRidgeCls-superblock-compact")),
    row("AOMRidgeCls-branch_global-compact", esc("AOMRidgeCls-branch_global-compact").replace("_", r"\_")),
    row("AOMRidgeCls-active-compact", esc("AOMRidgeCls-active-compact")),
    r"\bottomrule", r"\end{tabularx}",
]
OUT.write_text("\n".join(lines) + "\n")
print("\nWrote", OUT)
