#!/usr/bin/env python3
"""Full-cohort matched folded AOM versus explicitly materialized HPO.

This control holds the task, seed, folds, compact operator bank, candidate
grids, selection metric, tie rule and final refit constant.  It runs both the
paper's five-fold protocol and a three-fold sensitivity matching the fold count
of the archived broad HPO campaign.
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
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_info, threadpool_limits

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aom_nirs.pls.banks import compact_bank
from aom_nirs.ridge.solvers import make_alpha_grid
from paper.repro.reviewer_controls.folded_materialized_control import (
    _max_abs,
    _max_rel,
    _pls_run,
    _read_xy,
    _ridge_run,
    _winner_margin,
)


DEFAULT_DATA_ROOT = (REPO_ROOT.parent / "nirs4all-data" / "regression").resolve()
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "full_matched_hpo"


@dataclass(frozen=True)
class TaskSpec:
    name: str
    relative_dir: str


# Frozen strict N=32 intersection used by the manuscript's eight-variant panel.
TASKS = (
    TaskSpec("ALPINE_P_291_KS", "ALPINE/ALPINE_P_291_KS"),
    TaskSpec("An_spxyG70_30_byCultivar_ASD", "GRAPEVINE_LeafTraits/An_spxyG70_30_byCultivar_ASD"),
    TaskSpec("An_spxyG70_30_byCultivar_MicroNIR", "GRAPEVINE_LeafTraits/An_spxyG70_30_byCultivar_MicroNIR"),
    TaskSpec("An_spxyG70_30_byCultivar_MicroNIR_NeoSpectra", "GRAPEVINE_LeafTraits/An_spxyG70_30_byCultivar_MicroNIR_NeoSpectra"),
    TaskSpec("An_spxyG70_30_byCultivar_NeoSpectra", "GRAPEVINE_LeafTraits/An_spxyG70_30_byCultivar_NeoSpectra"),
    TaskSpec("Beef_Marbling_RandomSplit", "BEEFMARBLING/Beef_Marbling_RandomSplit"),
    TaskSpec("Beer_OriginalExtract_60_KS", "BEER/Beer_OriginalExtract_60_KS"),
    TaskSpec("Beer_OriginalExtract_60_YbaseSplit", "BEER/Beer_OriginalExtract_60_YbaseSplit"),
    TaskSpec("Biscuit_Fat_40_RandomSplit", "BISCUIT/Biscuit_Fat_40_RandomSplit"),
    TaskSpec("Biscuit_Sucrose_40_RandomSplit", "BISCUIT/Biscuit_Sucrose_40_RandomSplit"),
    TaskSpec("C_woOutlier", "COLZA/C_woOutlier"),
    TaskSpec("Ccar_spxyG_block2deg", "ECOSIS_LeafTraits/Ccar_spxyG_block2deg"),
    TaskSpec("Corn_Oil_80_ZhengChenPelegYbaseSplit", "CORN/Corn_Oil_80_ZhengChenPelegYbaseSplit"),
    TaskSpec("Corn_Starch_80_ZhengChenPelegYbaseSplit", "CORN/Corn_Starch_80_ZhengChenPelegYbaseSplit"),
    TaskSpec("DIESEL_bp50_246_b-a", "DIESEL/DIESEL_bp50_246_b-a"),
    TaskSpec("DIESEL_bp50_246_hla-b", "DIESEL/DIESEL_bp50_246_hla-b"),
    TaskSpec("DIESEL_bp50_246_hlb-a", "DIESEL/DIESEL_bp50_246_hlb-a"),
    TaskSpec("Fv_Fm_grp70_30", "FUSARIUM/Fv_Fm_grp70_30"),
    TaskSpec("LMA_spxyG70_30_byCultivar_ASD", "GRAPEVINE_LeafTraits/LMA_spxyG70_30_byCultivar_ASD"),
    TaskSpec("N_wOutlier", "COLZA/N_wOutlier"),
    TaskSpec("N_woOutlier", "COLZA/N_woOutlier"),
    TaskSpec("Rd25_CBtestSite", "DarkResp/Rd25_CBtestSite"),
    TaskSpec("Rd25_GTtestSite", "DarkResp/Rd25_GTtestSite"),
    TaskSpec("Rd25_XSBNtestSite", "DarkResp/Rd25_XSBNtestSite"),
    TaskSpec("Rd25_spxy70", "DarkResp/Rd25_spxy70"),
    TaskSpec("Rice_Amylose_313_YbasedSplit", "AMYLOSE/Rice_Amylose_313_YbasedSplit"),
    TaskSpec("TIC_spxy70", "IncombustibleMaterial/TIC_spxy70"),
    TaskSpec("WUEinst_spxyG70_30_byCultivar_MicroNIR_NeoSpectra", "GRAPEVINE_LeafTraits/WUEinst_spxyG70_30_byCultivar_MicroNIR_NeoSpectra"),
    TaskSpec("brix_groupSampleID_stratDateVar_balRows", "BERRY/brix_groupSampleID_stratDateVar_balRows"),
    TaskSpec("grapevine_chloride_556_KS", "GRAPEVINES/grapevine_chloride_556_KS"),
    TaskSpec("ph_groupSampleID_stratDateVar_balRows", "BERRY/ph_groupSampleID_stratDateVar_balRows"),
    TaskSpec("ta_groupSampleID_stratDateVar_balRows", "BERRY/ta_groupSampleID_stratDateVar_balRows"),
)


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
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


def _one_job(payload: dict[str, Any]) -> dict[str, Any]:
    spec = TaskSpec(**payload["task"])
    data_root = Path(payload["data_root"])
    seed = int(payload["seed"])
    cv = int(payload["cv"])
    max_components = int(payload["max_components"])
    alpha_grid_size = int(payload["alpha_grid_size"])
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=1):
            X_train, X_test, y_train, y_test, provenance = _read_xy(data_root / spec.relative_dir)
            operators = compact_bank(p=X_train.shape[1])
            names = [operator.name for operator in operators]
            if len(names) != 9:
                raise AssertionError(f"expected 9 compact operators, found {len(names)}")
            folds = list(KFold(n_splits=cv, shuffle=True, random_state=seed).split(X_train, y_train))
            k_grid = np.arange(
                1,
                min(max_components, len(X_train) - max(len(test) for _, test in folds), X_train.shape[1])
                + 1,
            )
            Xc_full = X_train - X_train.mean(axis=0)
            alpha_grid = make_alpha_grid(
                Xc_full @ Xc_full.T, n_grid=alpha_grid_size, low=-6.0, high=6.0
            )
            functions = {
                "PLS": lambda mode: _pls_run(
                    mode, X_train, X_test, y_train, y_test, folds, operators, k_grid
                ),
                "Ridge": lambda mode: _ridge_run(
                    mode, X_train, X_test, y_train, y_test, folds, operators, alpha_grid
                ),
            }
            rows: list[dict[str, Any]] = []
            candidates: list[dict[str, Any]] = []
            for model, function in functions.items():
                # Alternate execution order deterministically to limit warm-cache bias.
                folded_first = (sum(spec.name.encode()) + seed + cv + (model == "Ridge")) % 2 == 0
                order = ("folded", "materialized") if folded_first else ("materialized", "folded")
                outcomes = {mode: function(mode) for mode in order}
                folded = outcomes["folded"]
                materialized = outcomes["materialized"]
                for mode, outcome in outcomes.items():
                    grid = k_grid if model == "PLS" else alpha_grid
                    for op_idx, operator_name in enumerate(names):
                        for grid_idx, hyperparameter in enumerate(grid):
                            candidates.append(
                                {
                                    "task": spec.name,
                                    "seed": seed,
                                    "cv": cv,
                                    "model": model,
                                    "mode": mode,
                                    "operator_index": op_idx,
                                    "operator": operator_name,
                                    "grid_index": grid_idx,
                                    "hyperparameter": float(hyperparameter),
                                    "cv_rmse": float(outcome["scores"][op_idx, grid_idx]),
                                }
                            )
                rows.append(
                    {
                        "task": spec.name,
                        "seed": seed,
                        "cv": cv,
                        "model": model,
                        "n_train": len(X_train),
                        "n_test": len(X_test),
                        "n_features": X_train.shape[1],
                        "folded_operator": folded["selected_operator"],
                        "materialized_operator": materialized["selected_operator"],
                        "operator_agreement": folded["selected_operator"]
                        == materialized["selected_operator"],
                        "folded_hyperparameter": folded["selected_hyperparameter"],
                        "materialized_hyperparameter": materialized["selected_hyperparameter"],
                        "hyperparameter_agreement": folded["selected_grid_idx"]
                        == materialized["selected_grid_idx"],
                        "folded_test_rmse": folded["test_rmse"],
                        "materialized_test_rmse": materialized["test_rmse"],
                        "max_abs_cv_score_diff": _max_abs(folded["scores"], materialized["scores"]),
                        "max_rel_cv_score_diff": _max_rel(folded["scores"], materialized["scores"]),
                        "max_abs_prediction_diff": _max_abs(
                            folded["prediction"], materialized["prediction"]
                        ),
                        "max_rel_prediction_diff": _max_rel(
                            folded["prediction"], materialized["prediction"]
                        ),
                        "max_abs_coef_diff": _max_abs(
                            folded["coef_original"], materialized["coef_original"]
                        ),
                        "max_rel_coef_diff": _max_rel(
                            folded["coef_original"], materialized["coef_original"]
                        ),
                        "folded_winner_margin": _winner_margin(folded["scores"]),
                        "materialized_winner_margin": _winner_margin(materialized["scores"]),
                        "folded_time_s": folded["time_s"],
                        "materialized_time_s": materialized["time_s"],
                        "materialized_over_folded_time": materialized["time_s"]
                        / folded["time_s"],
                        "execution_order": ">".join(order),
                        "parity_ok": bool(
                            folded["selected_operator"] == materialized["selected_operator"]
                            and folded["selected_grid_idx"] == materialized["selected_grid_idx"]
                            and np.allclose(
                                folded["prediction"], materialized["prediction"], atol=1e-6, rtol=1e-5
                            )
                        ),
                    }
                )
        return {
            "status": "ok",
            "task": spec.name,
            "seed": seed,
            "cv": cv,
            "rows": rows,
            "candidates": candidates,
            "provenance": provenance,
            "wall_s": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "error",
            "task": spec.name,
            "seed": seed,
            "cv": cv,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "wall_s": time.perf_counter() - started,
        }


def _write_outputs(
    output_dir: Path,
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    if rows:
        pd.DataFrame(rows).sort_values(["cv", "task", "seed", "model"]).to_csv(
            output_dir / "per_run_results.csv", index=False
        )
    if candidates:
        pd.DataFrame(candidates).sort_values(
            ["cv", "task", "seed", "model", "mode", "operator_index", "grid_index"]
        ).to_csv(output_dir / "candidate_scores.csv", index=False)
    pd.DataFrame(
        failures,
        columns=["status", "task", "seed", "cv", "error_type", "error", "wall_s"],
    ).to_csv(output_dir / "failures.csv", index=False)


def _summarize(frame: pd.DataFrame) -> list[dict[str, Any]]:
    summaries = []
    for (cv, model), group in frame.groupby(["cv", "model"], sort=True):
        summaries.append(
            {
                "cv": int(cv),
                "model": model,
                "n_runs": len(group),
                "n_tasks": group["task"].nunique(),
                "n_seeds": group["seed"].nunique(),
                "selection_agreement": int(
                    (group["operator_agreement"] & group["hyperparameter_agreement"]).sum()
                ),
                "parity_ok": int(group["parity_ok"].sum()),
                "median_folded_time_s": float(group["folded_time_s"].median()),
                "median_materialized_time_s": float(group["materialized_time_s"].median()),
                "median_materialized_over_folded_time": float(
                    group["materialized_over_folded_time"].median()
                ),
                "total_folded_cpu_s": float(group["folded_time_s"].sum()),
                "total_materialized_cpu_s": float(group["materialized_time_s"].sum()),
                "max_abs_cv_score_diff": float(group["max_abs_cv_score_diff"].max()),
                "max_abs_prediction_diff": float(group["max_abs_prediction_diff"].max()),
                "max_abs_coef_diff": float(group["max_abs_coef_diff"].max()),
            }
        )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cv", nargs="+", type=int, default=[5, 3])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--max-components", type=int, default=25)
    parser.add_argument("--alpha-grid-size", type=int, default=50)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--tasks", nargs="*", default=[task.name for task in TASKS])
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 5:
        parser.error("--max-workers must be in [1, 5]")
    host_cpus = os.cpu_count() or 1
    if host_cpus - args.max_workers < 2:
        parser.error("resource policy requires leaving at least two CPUs free")
    if any(cv < 2 for cv in args.cv):
        parser.error("all CV fold counts must be >=2")
    selected = [task for task in TASKS if task.name in set(args.tasks)]
    unknown = sorted(set(args.tasks) - {task.name for task in TASKS})
    if unknown:
        parser.error(f"unknown tasks: {unknown}")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    original_affinity, active_affinity = _restrict_affinity(args.max_workers)
    jobs = [
        {
            "task": {"name": task.name, "relative_dir": task.relative_dir},
            "data_root": str(args.data_root.expanduser().resolve()),
            "seed": seed,
            "cv": cv,
            "max_components": args.max_components,
            "alpha_grid_size": args.alpha_grid_size,
        }
        for cv in args.cv
        for seed in args.seeds
        for task in selected
    ]
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}
    completed = 0
    with ProcessPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {pool.submit(_one_job, payload): payload for payload in jobs}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result["status"] == "ok":
                rows.extend(result["rows"])
                candidates.extend(result["candidates"])
                provenance[result["task"]] = result["provenance"]
                print(
                    f"[{completed}/{len(jobs)}] cv={result['cv']} seed={result['seed']} "
                    f"{result['task']} {result['wall_s']:.2f}s",
                    flush=True,
                )
            else:
                failures.append(result)
                print(
                    f"[{completed}/{len(jobs)}] ERROR cv={result['cv']} seed={result['seed']} "
                    f"{result['task']}: {result['error']}",
                    flush=True,
                )
            _write_outputs(output_dir, rows, candidates, failures)
    frame = pd.DataFrame(rows)
    summaries = _summarize(frame) if len(frame) else []
    summary = {
        "protocol": "compact9-folded-vs-materialized-cv5-cv3",
        "git_revision": _git_revision(),
        "tasks_requested": len(selected),
        "job_count": len(jobs),
        "successful_jobs": len(jobs) - len(failures),
        "failed_jobs": len(failures),
        "cv": args.cv,
        "seeds": args.seeds,
        "operator_count": 9,
        "max_components": args.max_components,
        "alpha_grid_size": args.alpha_grid_size,
        "max_workers": args.max_workers,
        "host_cpu_count": os.cpu_count(),
        "gpu_visible": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "original_cpu_affinity": original_affinity,
        "active_cpu_affinity": active_affinity,
        "wall_time_s": time.perf_counter() - started,
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
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(summaries).to_csv(output_dir / "summary.csv", index=False)
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if not failures and len(frame) == len(jobs) * 2 and frame["parity_ok"].all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
