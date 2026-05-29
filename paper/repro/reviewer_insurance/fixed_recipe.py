#!/usr/bin/env python3
"""A4-res — pre-registered FIXED conventional recipe baseline (PLS and Ridge).

Recipe (fixed a priori, NOT searched): SNV -> Savitzky-Golay 1st derivative (window 15, polyorder 2)
-> PLS (n_components by 5-fold CV, 1..min(15,n-1)) / Ridge (alpha by 5-fold CV, log grid).
Reads the LOCAL (gitignored) NIR data via nirs4all-lab cohort paths. Compares the fixed recipe to
plain PLS and to AOM-PLS (compact-cv5) on the paired denominator. Writes table_fixed_recipe.tex.
"""
import os, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error

LAB = "/home/delete/nirs4all/nirs4all-lab"
COHORT = f"{LAB}/cohort_selection/cohort_regression.csv"
RUNS = "/home/delete/nirs4all/nirs4all-aom/benchmarks/runs"
OUTCSV = "/home/delete/nirs4all/nirs4all-aom/paper/repro/reviewer_insurance/fixed_recipe_results.csv"
OUTTEX = "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_fixed_recipe.tex"
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
        r = (num.loc[common] / den.loc[common]).dropna()
        return label, len(r), float(r.median()), int((r < 1).sum())
    rows = []
    # PLS-fixed vs plain PLS
    pf = ok["rmsep_pls_fixed"]
    rows.append(ratios(pf, pls_std, "PLS-fixed-recipe vs PLS-standard"))
    # AOM-PLS vs PLS-fixed (the key reviewer question)
    rows.append(ratios(aom, pf, "AOM-PLS (compact-cv5) vs PLS-fixed-recipe"))
    for lab, n, m, w in rows:
        print(f"  {lab}: N={n}  median ratio={m:.3f}  wins={w}/{n}")

    # LaTeX fragment
    esc = lambda s: s.replace("-", r"-\allowbreak{}")
    lines = [r"\begin{tabularx}{\linewidth}{Xrrr}", r"\toprule",
             r"Comparison & $N$ & Median RMSEP ratio & Wins \\", r"\midrule"]
    for lab, n, m, w in rows:
        lines.append(rf"{esc(lab)} & {n} & {m:.3f} & {w}/{n} \\")
    lines += [r"\bottomrule", r"\end{tabularx}"]
    open(OUTTEX, "w").write("\n".join(lines) + "\n")
    print("Wrote", OUTTEX)

if __name__ == "__main__":
    main()
