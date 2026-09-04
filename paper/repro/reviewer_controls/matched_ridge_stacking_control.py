#!/usr/bin/env python3
"""Matched compact-bank Ridge stacking control for the AOM Talanta paper.

This is an SPRR-inspired control, not a claimed reproduction of SPRR or
PROSAC.  It fits one Ridge base learner per member of the same nine-operator
strict-linear bank used by AOM-Ridge, obtains out-of-fold predictions on the
same five folds, and combines the nine views with a Ridge meta-model.  The
external test split is touched only once, after all base and meta choices.

The comparison against AOM-Ridge is path-matched to
``full_matched_hpo_control.py``: task, seed, folds, operator bank, alpha-grid
rule, selection metric and external split are identical.  CPU affinity and
thread limits enforce the revision resource policy; CUDA is disabled.
"""

# ruff: noqa: E402 -- resource limits must precede NumPy/SciPy imports.

from __future__ import annotations

import os

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import stats
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_info, threadpool_limits

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aom_nirs.pls.banks import compact_bank
from aom_nirs.ridge.solvers import make_alpha_grid, solve_dual_ridge_path_eigh
from paper.repro.reviewer_controls.folded_materialized_control import _read_xy, _rmse
from paper.repro.reviewer_controls.full_matched_hpo_control import (
    DEFAULT_DATA_ROOT,
    TASKS,
    TaskSpec,
)


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "matched_ridge_stacking"
DEFAULT_AOM_RESULTS = HERE / "full_matched_hpo" / "per_run_results.csv"
BOOTSTRAP_SEED = 20260904
BOOTSTRAP_N = 20_000


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _restrict_affinity(max_workers: int) -> tuple[list[int], list[int]]:
    if not hasattr(os, "sched_getaffinity"):
        return [], []
    original = sorted(os.sched_getaffinity(0))
    active = original[:max_workers]
    os.sched_setaffinity(0, active)
    return original, sorted(os.sched_getaffinity(0))


def _ridge_predictions(
    X_train: np.ndarray,
    X_left: np.ndarray,
    y_train: np.ndarray,
    alpha_grid: np.ndarray,
) -> np.ndarray:
    """Return predictions for every alpha, with fold-local centering."""

    x_mean = X_train.mean(axis=0)
    y_mean = float(y_train.mean())
    Z_train = X_train - x_mean
    Z_left = X_left - x_mean
    kernel = Z_train @ Z_train.T
    kernel = 0.5 * (kernel + kernel.T)
    dual_path = solve_dual_ridge_path_eigh(kernel, y_train - y_mean, alpha_grid)
    return Z_left @ Z_train.T @ dual_path.T + y_mean


def _fit_stacking(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    *,
    seed: int,
    cv: int,
    alpha_grid_size: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    operators = compact_bank(p=X_train.shape[1])
    operator_names = [operator.name for operator in operators]
    if len(operators) != 9:
        raise AssertionError(f"expected nine compact operators, found {len(operators)}")

    folds = list(KFold(n_splits=cv, shuffle=True, random_state=seed).split(X_train, y_train))
    centered = X_train - X_train.mean(axis=0)
    base_alpha_grid = make_alpha_grid(
        centered @ centered.T,
        n_grid=alpha_grid_size,
        low=-6.0,
        high=6.0,
    )

    n_train = len(X_train)
    n_test = len(X_test)
    oof = np.empty((n_train, len(operators)), dtype=float)
    test_views = np.empty((n_test, len(operators)), dtype=float)
    base_cv_rmse: list[float] = []
    selected_base_alpha: list[float] = []

    for op_index, operator in enumerate(operators):
        fold_scores = np.empty((len(folds), len(base_alpha_grid)), dtype=float)
        oof_path = np.empty((len(base_alpha_grid), n_train), dtype=float)
        for fold_index, (train_index, valid_index) in enumerate(folds):
            X_fold = X_train[train_index]
            X_valid = X_train[valid_index]
            y_fold = y_train[train_index]
            y_valid = y_train[valid_index]
            x_mean = X_fold.mean(axis=0)
            operator.fit(X_fold - x_mean)
            Z_fold = operator.transform(X_fold - x_mean)
            Z_valid = operator.transform(X_valid - x_mean)
            predictions = _ridge_predictions(
                Z_fold,
                Z_valid,
                y_fold,
                base_alpha_grid,
            )
            oof_path[:, valid_index] = predictions.T
            fold_scores[fold_index] = np.sqrt(
                np.mean((predictions - y_valid[:, None]) ** 2, axis=0)
            )
        mean_scores = fold_scores.mean(axis=0)
        selected = int(np.argmin(mean_scores))
        selected_base_alpha.append(float(base_alpha_grid[selected]))
        base_cv_rmse.append(float(mean_scores[selected]))
        oof[:, op_index] = oof_path[selected]

        x_mean = X_train.mean(axis=0)
        operator.fit(X_train - x_mean)
        Z_train = operator.transform(X_train - x_mean)
        Z_test = operator.transform(X_test - x_mean)
        test_views[:, op_index] = _ridge_predictions(
            Z_train,
            Z_test,
            y_train,
            np.asarray([base_alpha_grid[selected]]),
        )[:, 0]

    meta_centered = oof - oof.mean(axis=0)
    meta_alpha_grid = make_alpha_grid(
        meta_centered @ meta_centered.T,
        n_grid=alpha_grid_size,
        low=-6.0,
        high=6.0,
    )
    meta_fold_scores = np.empty((len(folds), len(meta_alpha_grid)), dtype=float)
    for fold_index, (train_index, valid_index) in enumerate(folds):
        predictions = _ridge_predictions(
            oof[train_index],
            oof[valid_index],
            y_train[train_index],
            meta_alpha_grid,
        )
        meta_fold_scores[fold_index] = np.sqrt(
            np.mean((predictions - y_train[valid_index, None]) ** 2, axis=0)
        )
    meta_scores = meta_fold_scores.mean(axis=0)
    selected_meta = int(np.argmin(meta_scores))
    meta_alpha = float(meta_alpha_grid[selected_meta])
    prediction = _ridge_predictions(
        oof,
        test_views,
        y_train,
        np.asarray([meta_alpha]),
    )[:, 0]

    return {
        "stacking_test_rmse": _rmse(y_test, prediction),
        "raw_ridge_test_rmse": _rmse(y_test, test_views[:, 0]),
        "selected_base_alpha_json": json.dumps(selected_base_alpha),
        "base_cv_rmse_json": json.dumps(base_cv_rmse),
        "selected_meta_alpha": meta_alpha,
        "meta_cv_rmse": float(meta_scores[selected_meta]),
        "operator_names_json": json.dumps(operator_names),
        "fit_time_s": float(time.perf_counter() - started),
    }


def _one_job(payload: dict[str, Any]) -> dict[str, Any]:
    spec = TaskSpec(**payload["task"])
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=1):
            X_train, X_test, y_train, y_test, provenance = _read_xy(
                Path(payload["data_root"]) / spec.relative_dir
            )
            outcome = _fit_stacking(
                X_train,
                X_test,
                y_train,
                y_test,
                seed=int(payload["seed"]),
                cv=int(payload["cv"]),
                alpha_grid_size=int(payload["alpha_grid_size"]),
            )
        return {
            "status": "ok",
            "task": spec.name,
            "seed": int(payload["seed"]),
            "cv": int(payload["cv"]),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": X_train.shape[1],
            **outcome,
            "provenance": provenance,
            "wall_s": float(time.perf_counter() - started),
        }
    except Exception as exc:
        return {
            "status": "error",
            "task": spec.name,
            "seed": int(payload["seed"]),
            "cv": int(payload["cv"]),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "wall_s": float(time.perf_counter() - started),
        }


def _paired_summary(
    frame: pd.DataFrame,
    *,
    candidate: str,
    reference: str,
    label: str,
) -> dict[str, Any]:
    task_means = frame.groupby("task")[[candidate, reference]].mean().dropna()
    task_means = task_means[(task_means[candidate] > 0) & (task_means[reference] > 0)]
    ratios = (task_means[candidate] / task_means[reference]).to_numpy(float)
    differences = (task_means[candidate] - task_means[reference]).to_numpy(float)
    log_ratios = np.log(ratios)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(ratios, size=(BOOTSTRAP_N, len(ratios)), replace=True)
    medians = np.median(draws, axis=1)
    p = (
        float(stats.wilcoxon(log_ratios, alternative="two-sided", zero_method="wilcox").pvalue)
        if np.any(log_ratios != 0)
        else math.nan
    )
    return {
        "comparison": label,
        "candidate": candidate,
        "reference": reference,
        "n": len(ratios),
        "median_ratio": float(np.median(ratios)),
        "ci95_low": float(np.percentile(medians, 2.5)),
        "ci95_high": float(np.percentile(medians, 97.5)),
        "wins": int(np.sum(differences < 0)),
        "ties": int(np.sum(differences == 0)),
        "losses": int(np.sum(differences > 0)),
        "wilcoxon_raw_two_sided_p": p,
    }


def _fmt_p(value: float) -> str:
    if not math.isfinite(value):
        return "NA"
    return f"{value:.2e}" if value < 0.001 else f"{value:.3f}"


def _write_report(output_dir: Path, summaries: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    lines = [
        "# Matched compact-bank Ridge stacking control",
        "",
        "This is an SPRR-inspired same-bank control, not a faithful reproduction of SPRR or PROSAC.",
        "Each of the nine strict-linear views has its own five-fold-tuned Ridge base learner; a five-fold-tuned Ridge meta-model combines out-of-fold base predictions. The external test split is untouched until final evaluation.",
        "",
        "| Comparison | N | Median RMSEP ratio | 95% bootstrap CI | Wins/ties/losses | Raw two-sided log-ratio Wilcoxon p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['comparison']} | {row['n']} | {row['median_ratio']:.3f} | "
            f"{row['ci95_low']:.3f}--{row['ci95_high']:.3f} | "
            f"{row['wins']}/{row['ties']}/{row['losses']} | "
            f"{_fmt_p(row['wilcoxon_raw_two_sided_p'])} |"
        )
    lines += [
        "",
        f"Wall time: {metadata['wall_time_s']:.1f} s; workers: {metadata['max_workers']}; CUDA_VISIBLE_DEVICES={metadata['gpu_visible']!r}.",
    ]
    (output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_latex(summaries: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrrr}",
        r"\toprule",
        r"Comparison & $N$ & Median ratio & 95\% CI & Wins & Raw $p_2$ \\",
        r"\midrule",
    ]
    labels = {
        "SPRR-inspired Ridge stacking vs matched AOM-Ridge":
            r"SPRR-inspired Ridge stacking vs matched AOM-Ridge",
        "SPRR-inspired Ridge stacking vs matched raw Ridge":
            r"SPRR-inspired Ridge stacking vs matched raw Ridge",
    }
    for row in summaries:
        lines.append(
            f"{labels[row['comparison']]} & {row['n']} & {row['median_ratio']:.3f} & "
            f"{row['ci95_low']:.3f}--{row['ci95_high']:.3f} & "
            f"{row['wins']}/{row['n']} & {_fmt_p(row['wilcoxon_raw_two_sided_p'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    table_path = REPO_ROOT / "paper" / "tables" / "table_stacking_control.tex"
    table_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--aom-results", type=Path, default=DEFAULT_AOM_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cv", type=int, default=5)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--alpha-grid-size", type=int, default=50)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--tasks", nargs="*", default=[task.name for task in TASKS])
    args = parser.parse_args()

    if not 1 <= args.max_workers <= 5:
        parser.error("--max-workers must be in [1, 5]")
    host_cpus = os.cpu_count() or 1
    if host_cpus - args.max_workers < 2:
        parser.error("resource policy requires leaving at least two CPUs free")
    if args.cv < 2:
        parser.error("--cv must be >=2")
    task_by_name = {task.name: task for task in TASKS}
    unknown = sorted(set(args.tasks) - set(task_by_name))
    if unknown:
        parser.error(f"unknown tasks: {unknown}")
    selected = [task_by_name[name] for name in args.tasks]

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    original_affinity, active_affinity = _restrict_affinity(args.max_workers)
    jobs = [
        {
            "task": {"name": task.name, "relative_dir": task.relative_dir},
            "data_root": str(args.data_root.expanduser().resolve()),
            "seed": seed,
            "cv": args.cv,
            "alpha_grid_size": args.alpha_grid_size,
        }
        for seed in args.seeds
        for task in selected
    ]

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}
    with ProcessPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {pool.submit(_one_job, job): job for job in jobs}
        for completed, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result["status"] == "ok":
                provenance[result["task"]] = result.pop("provenance")
                rows.append(result)
                print(
                    f"[{completed}/{len(jobs)}] seed={result['seed']} {result['task']} "
                    f"{result['wall_s']:.2f}s",
                    flush=True,
                )
            else:
                failures.append(result)
                print(
                    f"[{completed}/{len(jobs)}] ERROR seed={result['seed']} "
                    f"{result['task']}: {result['error']}",
                    flush=True,
                )
            if rows:
                pd.DataFrame(rows).sort_values(["task", "seed"]).to_csv(
                    output_dir / "per_run_results.csv", index=False
                )
            pd.DataFrame(failures).to_csv(output_dir / "failures.csv", index=False)

    frame = pd.DataFrame(rows)
    if not frame.empty:
        matched = pd.read_csv(args.aom_results)
        matched = matched[(matched["cv"] == args.cv) & (matched["model"] == "Ridge")]
        matched = matched[["task", "seed", "folded_test_rmse"]]
        frame = frame.merge(matched, on=["task", "seed"], how="left", validate="one_to_one")
        frame.sort_values(["task", "seed"]).to_csv(output_dir / "per_run_results.csv", index=False)
        if frame["folded_test_rmse"].isna().any():
            missing = frame.loc[frame["folded_test_rmse"].isna(), ["task", "seed"]]
            raise RuntimeError(f"missing matched AOM rows:\n{missing.to_string(index=False)}")
        summaries = [
            _paired_summary(
                frame,
                candidate="stacking_test_rmse",
                reference="folded_test_rmse",
                label="SPRR-inspired Ridge stacking vs matched AOM-Ridge",
            ),
            _paired_summary(
                frame,
                candidate="stacking_test_rmse",
                reference="raw_ridge_test_rmse",
                label="SPRR-inspired Ridge stacking vs matched raw Ridge",
            ),
        ]
    else:
        summaries = []

    metadata = {
        "protocol": "compact9-ridge-oof-stacking-cv5",
        "interpretation": "SPRR-inspired comparator; not a faithful SPRR or PROSAC reproduction",
        "git_revision": _git_revision(),
        "tasks_requested": len(selected),
        "job_count": len(jobs),
        "successful_jobs": len(rows),
        "failed_jobs": len(failures),
        "cv": args.cv,
        "seeds": args.seeds,
        "operator_count": 9,
        "alpha_grid_size": args.alpha_grid_size,
        "max_workers": args.max_workers,
        "host_cpu_count": os.cpu_count(),
        "gpu_visible": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "original_cpu_affinity": original_affinity,
        "active_cpu_affinity": active_affinity,
        "wall_time_s": float(time.perf_counter() - started),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
        "threadpools": threadpool_info(),
        "summaries": summaries,
        "input_provenance": provenance,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(summaries).to_csv(output_dir / "summary.csv", index=False)
    _write_report(output_dir, summaries, metadata)
    _write_latex(summaries)
    print(json.dumps(metadata, indent=2), flush=True)
    return 0 if not failures and len(rows) == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
