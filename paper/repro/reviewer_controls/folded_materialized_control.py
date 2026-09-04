#!/usr/bin/env python3
"""Matched folded-vs-materialized reviewer control for AOM-PLS/AOM-Ridge.

The two paths share data, compact-bank order, folds, hyperparameter grids,
selection score, and deterministic row-major tie-break.  The materialized
path explicitly constructs ``X @ A.T``; the folded path never does so.
"""

# ruff: noqa: E402 -- thread limits and the local package path precede imports.

from __future__ import annotations

import os

# These limits must be set before importing NumPy/SciPy.
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
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_info, threadpool_limits

from aom_nirs.pls.banks import compact_bank
from aom_nirs.pls.operators import LinearSpectralOperator
from aom_nirs.pls.simpls import simpls_standard
from aom_nirs.ridge.solvers import make_alpha_grid, solve_dual_ridge_path_eigh


DEFAULT_DATA_ROOT = (REPO_ROOT.parent / "nirs4all-data" / "regression").resolve()
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"


@dataclass(frozen=True)
class TaskSpec:
    name: str
    relative_dir: str


TASKS = (
    TaskSpec("Beer_OriginalExtract_60_KS", "BEER/Beer_OriginalExtract_60_KS"),
    TaskSpec(
        "Corn_Oil_80_ZhengChenPelegYbaseSplit",
        "CORN/Corn_Oil_80_ZhengChenPelegYbaseSplit",
    ),
    TaskSpec(
        "An_spxyG70_30_byCultivar_MicroNIR",
        "GRAPEVINE_LeafTraits/An_spxyG70_30_byCultivar_MicroNIR",
    ),
    TaskSpec("DIESEL_bp50_246_hla-b", "DIESEL/DIESEL_bp50_246_hla-b"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_xy(task_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    paths = {
        "Xtrain": task_dir / "Xtrain.csv",
        "Xtest": task_dir / "Xtest.csv",
        "Ytrain": task_dir / "Ytrain.csv",
        "Ytest": task_dir / "Ytest.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing dataset files: " + ", ".join(missing))
    X_train = pd.read_csv(paths["Xtrain"], sep=";").to_numpy(dtype=float)
    X_test = pd.read_csv(paths["Xtest"], sep=";").to_numpy(dtype=float)
    y_train = pd.read_csv(paths["Ytrain"], sep=";").iloc[:, 0].to_numpy(dtype=float)
    y_test = pd.read_csv(paths["Ytest"], sep=";").iloc[:, 0].to_numpy(dtype=float)
    arrays = (X_train, X_test, y_train, y_test)
    if not all(np.all(np.isfinite(array)) for array in arrays):
        raise ValueError(f"non-finite values in {task_dir}")
    provenance = {key: {"path": str(path.resolve()), "sha256": _sha256(path)} for key, path in paths.items()}
    return X_train, X_test, y_train, y_test, provenance


def _dominant_direction(S: np.ndarray) -> np.ndarray:
    if S.ndim == 1:
        return S.copy()
    if S.shape[1] == 1:
        return S[:, 0].copy()
    U, _, _ = np.linalg.svd(S, full_matrices=False)
    return U[:, 0].copy()


def _coef_from_factors(Z: np.ndarray, P: np.ndarray, Q: np.ndarray, k: int) -> np.ndarray:
    return Z[:, :k] @ np.linalg.pinv(P[:, :k].T @ Z[:, :k]) @ Q[:, :k].T


def _folded_simpls_path(
    Xc: np.ndarray,
    Yc: np.ndarray,
    operator: LinearSpectralOperator,
    max_components: int,
) -> list[np.ndarray]:
    """Exact fixed-operator SIMPLS without materializing ``Xc A.T``.

    The SIMPLS loading basis is retained in transformed coordinates, while
    scores and deployable coefficients are computed on the original grid.
    """
    Y2 = Yc.reshape(-1, 1) if Yc.ndim == 1 else np.asarray(Yc, dtype=float)
    p = Xc.shape[1]
    operator.fit(Xc)
    S_b = operator.apply_cov(Xc.T @ Y2)
    if S_b.ndim == 1:
        S_b = S_b.reshape(-1, 1)
    Z = np.zeros((p, max_components))
    P = np.zeros((p, max_components))
    Q = np.zeros((Y2.shape[1], max_components))
    V_b = np.zeros((p, max_components))
    coefs: list[np.ndarray] = []
    eps = 1e-14
    for component in range(max_components):
        r = _dominant_direction(S_b)
        z = operator.adjoint_vec(r)
        t = Xc @ z
        t_norm = float(np.linalg.norm(t))
        if t_norm < eps:
            break
        t /= t_norm
        z /= t_norm
        p_original = Xc.T @ t
        p_transformed = operator.apply_cov(p_original)
        q_loading = Y2.T @ t
        v = p_transformed.copy()
        if component:
            v -= V_b[:, :component] @ (V_b[:, :component].T @ v)
        v_norm = float(np.linalg.norm(v))
        if v_norm < eps:
            break
        v /= v_norm
        S_b -= np.outer(v, v.T @ S_b)
        Z[:, component] = z
        P[:, component] = p_original
        Q[:, component] = q_loading
        V_b[:, component] = v
        coefs.append(_coef_from_factors(Z, P, Q, component + 1))
    return coefs


def _materialized_simpls_path(
    Xc: np.ndarray,
    Yc: np.ndarray,
    operator: LinearSpectralOperator,
    max_components: int,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Explicit SIMPLS path; returns transformed and original-grid coefs."""
    operator.fit(Xc)
    X_b = operator.transform(Xc)
    result = simpls_standard(X_b, Yc, max_components)
    transformed: list[np.ndarray] = []
    original: list[np.ndarray] = []
    for k in range(1, result.n_components + 1):
        beta_b = np.asarray(result.coef_prefix(k), dtype=float)
        if beta_b.ndim == 1:
            beta_b = beta_b.reshape(-1, 1)
        transformed.append(beta_b)
        original.append(operator.adjoint_vec(beta_b))
    return transformed, original


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    residual = np.asarray(y_true).ravel() - np.asarray(y_pred).ravel()
    return float(np.sqrt(np.mean(residual * residual)))


def _select_row_major(scores: np.ndarray) -> tuple[int, int]:
    """Stable tie-break: lowest operator index, then lowest grid index."""
    return tuple(int(value) for value in np.unravel_index(np.argmin(scores, axis=None), scores.shape))


def _pls_run(
    mode: str,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    operators: list[LinearSpectralOperator],
    k_grid: np.ndarray,
) -> dict:
    start = time.perf_counter()
    scores = np.full((len(operators), len(k_grid)), np.inf)
    max_k = int(k_grid.max())
    for op_idx, operator in enumerate(operators):
        fold_scores = np.full((len(folds), len(k_grid)), np.inf)
        for fold_idx, (train_idx, valid_idx) in enumerate(folds):
            X_tr, X_va = X_train[train_idx], X_train[valid_idx]
            y_tr, y_va = y_train[train_idx], y_train[valid_idx]
            x_mean = X_tr.mean(axis=0)
            y_mean = float(y_tr.mean())
            Xc_tr = X_tr - x_mean
            Xc_va = X_va - x_mean
            yc_tr = y_tr - y_mean
            if mode == "folded":
                coefs = _folded_simpls_path(Xc_tr, yc_tr, operator, max_k)
                for grid_idx, k in enumerate(k_grid):
                    if k <= len(coefs):
                        fold_scores[fold_idx, grid_idx] = _rmse(y_va, Xc_va @ coefs[k - 1] + y_mean)
            elif mode == "materialized":
                beta_b, _ = _materialized_simpls_path(Xc_tr, yc_tr, operator, max_k)
                Xb_va = operator.transform(Xc_va)
                for grid_idx, k in enumerate(k_grid):
                    if k <= len(beta_b):
                        fold_scores[fold_idx, grid_idx] = _rmse(y_va, Xb_va @ beta_b[k - 1] + y_mean)
            else:
                raise ValueError(mode)
        scores[op_idx] = fold_scores.mean(axis=0)
    selected_op, selected_k_idx = _select_row_major(scores)
    selected_k = int(k_grid[selected_k_idx])
    x_mean = X_train.mean(axis=0)
    y_mean = float(y_train.mean())
    Xc_train = X_train - x_mean
    Xc_test = X_test - x_mean
    operator = operators[selected_op]
    if mode == "folded":
        coefs = _folded_simpls_path(Xc_train, y_train - y_mean, operator, selected_k)
        coef_original = coefs[selected_k - 1]
        prediction = Xc_test @ coef_original + y_mean
    else:
        beta_b, beta_original = _materialized_simpls_path(
            Xc_train, y_train - y_mean, operator, selected_k
        )
        coef_original = beta_original[selected_k - 1]
        prediction = operator.transform(Xc_test) @ beta_b[selected_k - 1] + y_mean
    elapsed = time.perf_counter() - start
    return {
        "scores": scores,
        "selected_op_idx": selected_op,
        "selected_operator": operator.name,
        "selected_grid_idx": selected_k_idx,
        "selected_hyperparameter": selected_k,
        "coef_original": np.asarray(coef_original),
        "prediction": np.asarray(prediction).ravel(),
        "test_rmse": _rmse(y_test, prediction),
        "time_s": float(elapsed),
    }


def _ridge_kernels(
    mode: str,
    Xc_train: np.ndarray,
    Xc_left: np.ndarray,
    operator: LinearSpectralOperator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    operator.fit(Xc_train)
    if mode == "folded":
        AXt = operator.apply_cov(Xc_train.T)
        U = operator.adjoint_vec(AXt)
        K_train = Xc_train @ U
        K_left = Xc_left @ U
        K_train = 0.5 * (K_train + K_train.T)
        return K_train, K_left, U
    if mode == "materialized":
        Z_train = operator.transform(Xc_train)
        Z_left = operator.transform(Xc_left)
        K_train = Z_train @ Z_train.T
        K_train = 0.5 * (K_train + K_train.T)
        K_left = Z_left @ Z_train.T
        return K_train, K_left, Z_train.T
    raise ValueError(mode)


def _ridge_run(
    mode: str,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    operators: list[LinearSpectralOperator],
    alpha_grid: np.ndarray,
) -> dict:
    start = time.perf_counter()
    scores = np.zeros((len(operators), len(alpha_grid)))
    for op_idx, operator in enumerate(operators):
        fold_scores = np.zeros((len(folds), len(alpha_grid)))
        for fold_idx, (train_idx, valid_idx) in enumerate(folds):
            X_tr, X_va = X_train[train_idx], X_train[valid_idx]
            y_tr, y_va = y_train[train_idx], y_train[valid_idx]
            x_mean = X_tr.mean(axis=0)
            y_mean = float(y_tr.mean())
            Xc_tr = X_tr - x_mean
            Xc_va = X_va - x_mean
            yc_tr = y_tr - y_mean
            K_tr, K_va, _ = _ridge_kernels(mode, Xc_tr, Xc_va, operator)
            dual_path = solve_dual_ridge_path_eigh(K_tr, yc_tr, alpha_grid)
            for alpha_idx in range(len(alpha_grid)):
                prediction = K_va @ dual_path[alpha_idx] + y_mean
                fold_scores[fold_idx, alpha_idx] = _rmse(y_va, prediction)
        scores[op_idx] = fold_scores.mean(axis=0)
    selected_op, selected_alpha_idx = _select_row_major(scores)
    alpha = float(alpha_grid[selected_alpha_idx])
    x_mean = X_train.mean(axis=0)
    y_mean = float(y_train.mean())
    Xc_train = X_train - x_mean
    Xc_test = X_test - x_mean
    operator = operators[selected_op]
    K_train, K_test, mapping = _ridge_kernels(mode, Xc_train, Xc_test, operator)
    dual = solve_dual_ridge_path_eigh(K_train, y_train - y_mean, np.asarray([alpha]))[0]
    prediction = K_test @ dual + y_mean
    if mode == "folded":
        coef_original = mapping @ dual
    else:
        beta_b = mapping @ dual
        coef_original = operator.adjoint_vec(beta_b)
    elapsed = time.perf_counter() - start
    return {
        "scores": scores,
        "selected_op_idx": selected_op,
        "selected_operator": operator.name,
        "selected_grid_idx": selected_alpha_idx,
        "selected_hyperparameter": alpha,
        "coef_original": np.asarray(coef_original),
        "prediction": np.asarray(prediction).ravel(),
        "test_rmse": _rmse(y_test, prediction),
        "time_s": float(elapsed),
    }


def _max_abs(left: np.ndarray, right: np.ndarray) -> float:
    left_array = np.asarray(left)
    right_array = np.asarray(right)
    left_finite = np.isfinite(left_array)
    right_finite = np.isfinite(right_array)
    if not np.array_equal(left_finite, right_finite):
        return float("inf")
    if not np.any(left_finite):
        return 0.0
    return float(np.max(np.abs(left_array[left_finite] - right_array[right_finite])))


def _max_rel(left: np.ndarray, right: np.ndarray) -> float:
    right_array = np.asarray(right)
    finite = np.isfinite(right_array)
    scale = max(1.0, float(np.max(np.abs(right_array[finite])))) if np.any(finite) else 1.0
    return _max_abs(left, right) / scale


def _winner_margin(scores: np.ndarray) -> float:
    ordered = np.sort(np.asarray(scores).ravel())
    return float(ordered[1] - ordered[0]) if ordered.size >= 2 else float("nan")


def _timed_repeats(
    function: Callable[[str], dict], repeats: int
) -> tuple[dict[str, list[float]], dict[str, list[dict]]]:
    timings = {"folded": [], "materialized": []}
    outcomes = {"folded": [], "materialized": []}
    for repeat in range(repeats):
        order = ("folded", "materialized") if repeat % 2 == 0 else ("materialized", "folded")
        for mode in order:
            result = function(mode)
            timings[mode].append(result["time_s"])
            outcomes[mode].append(result)
    return timings, outcomes


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows_list[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_list)


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _restrict_cpu_affinity(limit: int) -> tuple[list[int], list[int]]:
    if not hasattr(os, "sched_getaffinity"):
        return [], []
    original = sorted(os.sched_getaffinity(0))
    active = original[: min(limit, len(original))]
    os.sched_setaffinity(0, active)
    return original, sorted(os.sched_getaffinity(0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tasks", nargs="*", default=[task.name for task in TASKS])
    parser.add_argument("--cv", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--max-components", type=int, default=15)
    parser.add_argument("--alpha-grid-size", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cpu-limit", type=int, default=5)
    parser.add_argument("--strict", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if not (1 <= args.cpu_limit <= 5):
        parser.error("--cpu-limit must be in [1, 5]")
    if args.repeats < 2:
        parser.error("--repeats must be >= 2 for repeated timings")
    original_affinity, active_affinity = _restrict_cpu_affinity(args.cpu_limit)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_specs = [task for task in TASKS if task.name in set(args.tasks)]
    unknown = sorted(set(args.tasks) - {task.name for task in TASKS})
    if unknown:
        parser.error(f"unknown tasks: {unknown}")
    if not selected_specs:
        parser.error("no tasks selected")

    result_rows: list[dict] = []
    timing_rows: list[dict] = []
    score_rows: list[dict] = []
    provenance_rows: dict = {}
    failures: list[str] = []
    bank_names: list[str] | None = None

    with threadpool_limits(limits=1):
        for task in selected_specs:
            task_dir = args.data_root.expanduser().resolve() / task.relative_dir
            X_train, X_test, y_train, y_test, provenance = _read_xy(task_dir)
            provenance_rows[task.name] = provenance
            operators = compact_bank(p=X_train.shape[1])
            current_names = [operator.name for operator in operators]
            if len(current_names) != 9:
                raise AssertionError(f"compact bank has {len(current_names)} operators, expected 9")
            if bank_names is None:
                bank_names = current_names
            elif current_names != bank_names:
                raise AssertionError("compact bank order changed across tasks")
            folds = list(
                KFold(n_splits=args.cv, shuffle=True, random_state=args.seed).split(X_train, y_train)
            )
            k_grid = np.arange(1, min(args.max_components, len(X_train) - 1, X_train.shape[1]) + 1)
            Xc_full = X_train - X_train.mean(axis=0)
            K_identity = Xc_full @ Xc_full.T
            alpha_grid = make_alpha_grid(
                K_identity, n_grid=args.alpha_grid_size, low=-6.0, high=6.0
            )

            for model, runner, grid in (
                ("PLS", _pls_run, k_grid),
                ("Ridge", _ridge_run, alpha_grid),
            ):
                def execute(mode: str, _runner=runner, _grid=grid) -> dict:
                    return _runner(
                        mode,
                        X_train,
                        X_test,
                        y_train,
                        y_test,
                        folds,
                        operators,
                        _grid,
                    )

                # Untimed parity pass, after one warm-up pass per method.
                execute("folded")
                execute("materialized")
                folded = execute("folded")
                materialized = execute("materialized")
                timings, outcomes = _timed_repeats(execute, args.repeats)
                op_agreement = folded["selected_op_idx"] == materialized["selected_op_idx"]
                hp_agreement = folded["selected_grid_idx"] == materialized["selected_grid_idx"]
                score_abs = _max_abs(folded["scores"], materialized["scores"])
                prediction_abs = _max_abs(folded["prediction"], materialized["prediction"])
                coef_abs = _max_abs(folded["coef_original"], materialized["coef_original"])
                score_rel = _max_rel(folded["scores"], materialized["scores"])
                prediction_rel = _max_rel(folded["prediction"], materialized["prediction"])
                coef_rel = _max_rel(folded["coef_original"], materialized["coef_original"])
                repeat_selection_ok = all(
                    outcome["selected_op_idx"] == folded["selected_op_idx"]
                    and outcome["selected_grid_idx"] == folded["selected_grid_idx"]
                    for mode_outcomes in outcomes.values()
                    for outcome in mode_outcomes
                )
                parity_ok = bool(
                    op_agreement
                    and hp_agreement
                    and repeat_selection_ok
                    and score_rel <= 1e-8
                    and prediction_rel <= 1e-8
                    and coef_rel <= 1e-7
                )
                if not parity_ok:
                    failures.append(f"{task.name}:{model}")
                folded_median = float(np.median(timings["folded"]))
                materialized_median = float(np.median(timings["materialized"]))
                result_rows.append(
                    {
                        "task": task.name,
                        "model": model,
                        "n_train": X_train.shape[0],
                        "n_test": X_test.shape[0],
                        "n_features": X_train.shape[1],
                        "folded_operator": folded["selected_operator"],
                        "materialized_operator": materialized["selected_operator"],
                        "operator_agreement": op_agreement,
                        "folded_hyperparameter": folded["selected_hyperparameter"],
                        "materialized_hyperparameter": materialized["selected_hyperparameter"],
                        "hyperparameter_agreement": hp_agreement,
                        "repeat_selection_agreement": repeat_selection_ok,
                        "folded_test_rmse": folded["test_rmse"],
                        "materialized_test_rmse": materialized["test_rmse"],
                        "max_abs_cv_score_diff": score_abs,
                        "max_rel_cv_score_diff": score_rel,
                        "max_abs_prediction_diff": prediction_abs,
                        "max_rel_prediction_diff": prediction_rel,
                        "max_abs_coef_diff": coef_abs,
                        "max_rel_coef_diff": coef_rel,
                        "folded_winner_margin": _winner_margin(folded["scores"]),
                        "materialized_winner_margin": _winner_margin(materialized["scores"]),
                        "folded_median_time_s": folded_median,
                        "materialized_median_time_s": materialized_median,
                        "materialized_over_folded_time": materialized_median / folded_median,
                        "parity_ok": parity_ok,
                    }
                )
                for mode, mode_timings in timings.items():
                    for repeat_idx, elapsed in enumerate(mode_timings, start=1):
                        timing_rows.append(
                            {
                                "task": task.name,
                                "model": model,
                                "mode": mode,
                                "repeat": repeat_idx,
                                "time_s": elapsed,
                                "selected_operator": outcomes[mode][repeat_idx - 1]["selected_operator"],
                                "selected_hyperparameter": outcomes[mode][repeat_idx - 1]["selected_hyperparameter"],
                            }
                        )
                for mode, result in (("folded", folded), ("materialized", materialized)):
                    for op_idx, operator_name in enumerate(current_names):
                        for grid_idx, grid_value in enumerate(grid):
                            score_rows.append(
                                {
                                    "task": task.name,
                                    "model": model,
                                    "mode": mode,
                                    "operator_index": op_idx,
                                    "operator": operator_name,
                                    "grid_index": grid_idx,
                                    "hyperparameter": grid_value,
                                    "cv_rmse_mean": result["scores"][op_idx, grid_idx],
                                }
                            )
                print(
                    f"{task.name} {model}: parity={parity_ok} "
                    f"selection={folded['selected_operator']}/{folded['selected_hyperparameter']:.8g} "
                    f"pred_abs={prediction_abs:.3e} coef_abs={coef_abs:.3e} "
                    f"time folded/materialized={folded_median:.4f}/{materialized_median:.4f}s"
                )

    _write_csv(output_dir / "per_task_results.csv", result_rows)
    _write_csv(output_dir / "timings.csv", timing_rows)
    _write_csv(output_dir / "candidate_scores.csv", score_rows)
    config = {
        "command": [sys.executable, *sys.argv],
        "git_revision": _git_revision(),
        "data_root": str(args.data_root.expanduser().resolve()),
        "tasks": [task.__dict__ for task in selected_specs],
        "data_provenance": provenance_rows,
        "compact_bank_names": bank_names,
        "cv": {"class": "KFold", "n_splits": args.cv, "shuffle": True, "random_state": args.seed},
        "pls_k_grid": list(range(1, args.max_components + 1)),
        "ridge_alpha_grid": "per-task identity-trace-relative: trace(Xc Xc.T)/n * logspace(-6,6,size)",
        "ridge_alpha_grid_size": args.alpha_grid_size,
        "tie_break": "np.argmin C-order: lowest operator index, then lowest hyperparameter-grid index",
        "timing_repeats": args.repeats,
        "warmup": "one unrecorded run per mode, followed by one parity run and alternating timed runs",
        "cpu_only": True,
        "cpu_affinity_original": original_affinity,
        "cpu_affinity_active": active_affinity,
        "thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "BLIS_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "CUDA_VISIBLE_DEVICES",
            )
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "threadpools": threadpool_info(),
        "parity_thresholds": {
            "max_relative_cv_score_difference": 1e-8,
            "max_relative_prediction_difference": 1e-8,
            "max_relative_original_coefficient_difference": 1e-7,
            "selected_operator_and_grid_index": "exact",
        },
    }
    (output_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    summary = {
        "tasks": len(selected_specs),
        "model_task_comparisons": len(result_rows),
        "all_parity_ok": not failures,
        "failed_comparisons": failures,
        "operator_agreements": sum(str(row["operator_agreement"]).lower() == "true" for row in result_rows),
        "hyperparameter_agreements": sum(str(row["hyperparameter_agreement"]).lower() == "true" for row in result_rows),
        "max_abs_cv_score_difference": max(row["max_abs_cv_score_diff"] for row in result_rows),
        "max_abs_prediction_difference": max(row["max_abs_prediction_diff"] for row in result_rows),
        "max_abs_original_coefficient_difference": max(row["max_abs_coef_diff"] for row in result_rows),
        "median_materialized_over_folded_time_by_model": {
            model: float(
                np.median(
                    [row["materialized_over_folded_time"] for row in result_rows if row["model"] == model]
                )
            )
            for model in ("PLS", "Ridge")
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
