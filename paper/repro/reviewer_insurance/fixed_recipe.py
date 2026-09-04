#!/usr/bin/env python3
"""A4-res — pre-registered FIXED conventional recipe baseline (PLS and Ridge).

Recipe (fixed a priori, NOT searched): SNV -> Savitzky-Golay 1st derivative (window 15, polyorder 2)
-> PLS (n_components by 5-fold CV, 1..min(15,n-1)) / Ridge (alpha by 5-fold CV, log grid).
Reads the LOCAL (gitignored) NIR data via nirs4all-lab cohort paths. Compares the fixed recipe to
plain PLS and to AOM-PLS (compact-cv5) on the paired denominator. Writes table_fixed_recipe.tex.
"""

# ruff: noqa: E402, E701, E702, E731 -- retained legacy script layout.

import os

_thread_limit = str(max(1, (os.cpu_count() or 1) - 2))
for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = _thread_limit
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from scipy.signal import savgol_filter
from scipy import stats
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error

REPO_ROOT = Path(__file__).resolve().parents[3]
LAB = os.environ.get("NIRS4ALL_LAB_DIR", str(REPO_ROOT.parent / "nirs4all-lab"))
COHORT = os.environ.get("AOM_FIXED_RECIPE_COHORT", f"{LAB}/cohort_selection/cohort_regression.csv")
RUNS = str(REPO_ROOT / "benchmarks/runs")
OUTCSV = os.environ.get("AOM_FIXED_RECIPE_RESULTS", str(Path(__file__).with_name("fixed_recipe_results.csv")))
OUTTEX = str(
    Path(os.environ.get("AOM_MANUSCRIPT_TABLES", REPO_ROOT / "paper/tables")).expanduser().resolve()
    / "table_fixed_recipe.tex"
)
RIDGE_RUN = f"{RUNS}/ridge/all54_headline/results.csv"
RMSE = lambda a, b: float(mean_squared_error(a, b) ** 0.5)

def snv_sg(X):
    X = (X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-8)
    return savgol_filter(X, 15, 2, deriv=1, axis=1)

def cv_pls(Xtr, ytr, seed):
    best = (1e18, 1)
    for k in range(1, min(16, Xtr.shape[0] - 1)):
        e = [RMSE(ytr[va], PLSRegression(k).fit(Xtr[tr], ytr[tr]).predict(Xtr[va]).ravel())
             for tr, va in KFold(5, shuffle=True, random_state=seed).split(Xtr)]
        if np.mean(e) < best[0]: best = (np.mean(e), k)
    return best[1]

def cv_ridge(Xtr, ytr, seed):
    grid = np.logspace(-3, 3, 13); best = (1e18, 1.0)
    for a in grid:
        e = [RMSE(ytr[va], Ridge(alpha=a).fit(Xtr[tr], ytr[tr]).predict(Xtr[va]).ravel())
             for tr, va in KFold(5, shuffle=True, random_state=seed).split(Xtr)]
        if np.mean(e) < best[0]: best = (np.mean(e), a)
    return best[1]

def run_one(row):
    d = row["dataset"]
    try:
        base = f"{LAB}/{os.path.dirname(row['train_path'])}"
        L = lambda f: pd.read_csv(f"{base}/{f}", sep=";").values
        Xtr, Xte = L("Xtrain.csv"), L("Xtest.csv")
        ytr, yte = L("Ytrain.csv").ravel(), L("Ytest.csv").ravel()
        if not (np.isfinite(Xtr).all() and np.isfinite(Xte).all() and np.isfinite(ytr).all()):
            return {"dataset": d, "status": "nan"}
        Xtr, Xte = snv_sg(Xtr), snv_sg(Xte)
        seeds = [0] if Xtr.shape[0] > 8000 else [0, 1, 2]
        pls = [RMSE(yte, PLSRegression(cv_pls(Xtr, ytr, s)).fit(Xtr, ytr).predict(Xte).ravel()) for s in seeds]
        rdg = [RMSE(yte, Ridge(alpha=cv_ridge(Xtr, ytr, s)).fit(Xtr, ytr).predict(Xte).ravel()) for s in seeds]
        return {"dataset": d, "status": "ok", "n_train": Xtr.shape[0], "p": Xtr.shape[1],
                "rmsep_pls_fixed": float(np.median(pls)), "rmsep_ridge_fixed": float(np.median(rdg))}
    except Exception as e:
        return {"dataset": d, "status": f"err:{type(e).__name__}"}

def main():
    if os.path.exists(OUTCSV):                       # reuse the (expensive) fixed-recipe fits
        res = pd.read_csv(OUTCSV)
        print(f"[cache] loaded {OUTCSV}")
    else:
        coh = pd.read_csv(COHORT)
        coh = coh[coh["status"] == "ok"] if "status" in coh.columns else coh
        res = pd.DataFrame([run_one(r) for _, r in coh.iterrows()])
        res.to_csv(OUTCSV, index=False)
    ok = res[res["status"] == "ok"].copy()
    print(f"fixed-recipe computed: {len(ok)}/{len(res)} ok; skipped: {res[res.status!='ok'].dataset.tolist()}")

    # comparison vs plain PLS and AOM-PLS (compact-cv5) from the seeds012 run
    run = pd.read_csv(f"{RUNS}/scenarios/paper_aom_aompls_seeds012/results.csv")
    run = run[run.get("status", "ok") == "ok"]
    def med(model):
        s = run[run["model"] == model]
        return s.groupby("dataset")["RMSEP"].median()
    pls_std, aom = med("PLS-standard-numpy"), med("AOM-compact-cv5-numpy")
    ok = ok.set_index("dataset")
    def ratios(num, den, label):
        common = [d for d in ok.index if d in num.index and d in den.index]
        paired = pd.concat(
            [num.loc[common].rename("candidate"), den.loc[common].rename("reference")],
            axis=1,
        ).dropna()
        r = (paired["candidate"] / paired["reference"]).to_numpy(float)
        delta = (paired["candidate"] - paired["reference"]).to_numpy(float)
        rng = np.random.default_rng(20260904)
        draw = rng.choice(r, size=(20_000, len(r)), replace=True)
        ci = np.percentile(np.median(draw, axis=1), [2.5, 97.5])
        p = float(stats.wilcoxon(delta, alternative="two-sided", zero_method="wilcox").pvalue)
        return label, len(r), float(np.median(r)), float(ci[0]), float(ci[1]), int((r < 1).sum()), p
    rows = []
    # PLS-fixed vs plain PLS
    pf = ok["rmsep_pls_fixed"]
    rows.append(ratios(pf, pls_std, "PLS-fixed-recipe vs PLS-standard"))
    # AOM-PLS vs PLS-fixed (the key reviewer question)
    rows.append(ratios(aom, pf, "AOM-PLS (compact-cv5) vs PLS-fixed-recipe"))

    # Ridge twin from the headline run: AOM-Ridge (simple global) and plain Ridge-raw
    rg = pd.read_csv(RIDGE_RUN)
    rg = rg[rg.get("status", "ok") == "ok"]
    medv = lambda v: rg[rg["variant"] == v].groupby("dataset")["rmsep"].median()
    ridge_raw, aom_ridge = medv("Ridge-raw"), medv("AOMRidge-global-compact-none")
    rf = ok["rmsep_ridge_fixed"]
    rows.append(ratios(rf, ridge_raw, "Ridge-fixed-recipe vs Ridge-raw"))
    rows.append(ratios(aom_ridge, rf, "AOM-Ridge (global) vs Ridge-fixed-recipe"))
    for lab, n, m, lo, hi, w, p in rows:
        print(
            f"  {lab}: N={n}  median ratio={m:.3f}  "
            f"95% CI={lo:.3f}--{hi:.3f}  wins={w}/{n}  raw p2={p:.4g}"
        )

    # LaTeX fragment
    esc = lambda s: s.replace("-", r"-\allowbreak{}")
    lines = [r"\begin{tabularx}{\linewidth}{Xrrrrr}", r"\toprule",
             r"Comparison & $N$ & Median RMSEP ratio & 95\% CI & Wins & Raw $p_2$ \\", r"\midrule"]
    for lab, n, m, lo, hi, w, p in rows:
        p_text = f"{p:.1e}" if p < 0.001 else f"{p:.3f}"
        lines.append(rf"{esc(lab)} & {n} & {m:.3f} & {lo:.3f}--{hi:.3f} & {w}/{n} & {p_text} \\")
    lines += [r"\bottomrule", r"\end{tabularx}"]
    Path(OUTTEX).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", OUTTEX)

if __name__ == "__main__":
    main()
