#!/usr/bin/env python3
"""Matched identity-only PLS-DA versus compact-bank AOM-PLS-DA control.

Both methods use the exact same external split, stratified inner folds,
class-balanced response coding, component grid, PLS engine, and logistic
calibrator.  The only difference is the candidate operator set: identity
alone versus the nine-operator compact bank.

The runner is resumable at the (dataset, seed) level and never writes into the
frozen paper benchmark workspaces.  CPU parallelism is capped at five worker
processes; callers should also launch it with BLAS/OpenMP thread limits of one.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# These must be set before importing NumPy/scikit-learn.  They are defaults,
# so an explicitly stricter launcher setting remains authoritative.
for _name in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ.setdefault(_name, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scipy  # noqa: E402
import sklearn  # noqa: E402
from scipy.stats import binomtest, wilcoxon  # noqa: E402
from sklearn.exceptions import ConvergenceWarning  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import StratifiedKFold  # noqa: E402
from sklearn.preprocessing import LabelEncoder  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from aom_nirs.pls.banks import compact_bank  # noqa: E402
from aom_nirs.pls.classification import _class_balanced_encode  # noqa: E402
from aom_nirs.pls.metrics import (  # noqa: E402
    balanced_accuracy,
    expected_calibration_error,
    log_loss,
    macro_f1,
)
from aom_nirs.pls.selection import _resolve_engine  # noqa: E402


PROTOCOL_ID = "matched-plsda-cv5-v1"
METHOD_IDENTITY = "PLS-DA-identity-matched"
METHOD_AOM = "AOM-PLS-DA-compact9-matched"
RAW_FIELDS = [
    "protocol_id", "database_name", "dataset", "seed", "method", "status",
    "status_details", "n_train", "n_test", "n_features", "n_classes",
    "class_counts_train_json", "class_counts_test_json", "external_split_files_json",
    "fold_hash", "cv_folds", "k_grid", "candidate_operators", "selected_operator_index",
    "selected_operator", "selected_k", "cv_balanced_log_loss", "balanced_accuracy",
    "macro_f1", "log_loss", "ece_10_equal_width", "n_unique_test_spectra",
    "duplicate_test_excess", "balanced_accuracy_unique_test_spectra",
    "log_loss_unique_test_spectra", "fit_select_time_s", "predict_time_s",
    "input_sha256_json", "warnings_json",
]


def _read_x(path: Path) -> np.ndarray:
    frame = pd.read_csv(path, sep=";")
    try:
        return frame.to_numpy(dtype=np.float64)
    except ValueError:
        # A few source CSVs mix decimal points with European decimal commas in
        # scientific notation.  Match the frozen benchmark loader exactly.
        for column in frame.select_dtypes(include="object").columns:
            frame[column] = frame[column].astype(str).str.replace(",", ".", regex=False)
        return frame.to_numpy(dtype=np.float64)


def _read_y(path: Path) -> np.ndarray:
    return pd.read_csv(path, sep=";").iloc[:, 0].to_numpy()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_split(row: dict[str, Any], data_root: Path) -> dict[str, Path]:
    base = data_root / "classification" / str(row["database_name"]) / str(row["dataset"])
    standard = {
        "x_train": base / "Xtrain.csv", "x_test": base / "Xtest.csv",
        "y_train": base / "Ytrain.csv", "y_test": base / "Ytest.csv",
    }
    if all(path.is_file() for path in standard.values()):
        return standard
    calval = {
        "x_train": base / "Xcal.csv", "x_test": base / "Xval.csv",
        "y_train": base / "Ycal.csv", "y_test": base / "Yval.csv",
    }
    if all(path.is_file() for path in calval.values()):
        return calval
    missing = [str(path) for path in standard.values() if not path.is_file()]
    raise FileNotFoundError("external split files missing: " + ", ".join(missing))


def _align_proba(proba: np.ndarray, fitted_classes: np.ndarray, n_classes: int) -> np.ndarray:
    aligned = np.zeros((len(proba), n_classes), dtype=float)
    for source, cls in enumerate(fitted_classes.astype(int)):
        aligned[:, cls] = proba[:, source]
    return aligned


def _balanced_log_loss(y: np.ndarray, proba: np.ndarray) -> float:
    losses = []
    for cls in np.unique(y):
        mask = y == cls
        losses.append(-np.mean(np.log(np.clip(proba[mask, int(cls)], 1e-12, 1.0))))
    return float(np.mean(losses))


def _fit_latent(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    classes: np.ndarray,
    bank: list[Any],
    op_index: int,
    max_components: int,
) -> tuple[Any, np.ndarray, np.ndarray]:
    x_mean = X_train.mean(axis=0)
    Y = _class_balanced_encode(y_train, classes)
    y_mean = Y.mean(axis=0)
    Xc = X_train - x_mean
    Yc = Y - y_mean
    bank[op_index].fit(X_train, y_train)
    result = _resolve_engine(
        "simpls_covariance", Xc, Yc, bank, [op_index] * max_components,
        max_components, "transformed",
    )
    return result, result.T, (X_eval - x_mean) @ result.Z


def _fit_calibrator(T: np.ndarray, y: np.ndarray, seed: int) -> LogisticRegression:
    model = LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=seed, solver="lbfgs"
    )
    model.fit(T, y)
    return model


def _row_hashes(X: np.ndarray) -> np.ndarray:
    contiguous = np.ascontiguousarray(X)
    return np.asarray(
        [hashlib.sha256(contiguous[i].view(np.uint8)).hexdigest() for i in range(len(X))],
        dtype=object,
    )


def _evaluate_job(job: dict[str, Any]) -> list[dict[str, Any]]:
    with threadpool_limits(limits=1):
        started = time.perf_counter()
        row = job["row"]
        seed = int(job["seed"])
        paths = {key: Path(value) for key, value in job["paths"].items()}
        X_train, X_test = _read_x(paths["x_train"]), _read_x(paths["x_test"])
        y_train_raw, y_test_raw = _read_y(paths["y_train"]), _read_y(paths["y_test"])
        if not np.isfinite(X_train).all() or not np.isfinite(X_test).all():
            raise ValueError("non-finite spectra")
        encoder = LabelEncoder().fit(y_train_raw)
        if not set(np.unique(y_test_raw)).issubset(set(encoder.classes_)):
            raise ValueError("test split contains a class absent from training")
        y_train = encoder.transform(y_train_raw).astype(int)
        y_test = encoder.transform(y_test_raw).astype(int)
        classes = np.arange(len(encoder.classes_), dtype=int)
        n_splits = int(job["cv"])
        k_max = min(int(job["max_components"]), len(X_train) - 1, X_train.shape[1])
        k_grid = list(range(1, k_max + 1))
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        folds = [(tr, va) for tr, va in splitter.split(X_train, y_train)]
        fold_hash = hashlib.sha256(
            json.dumps(
                [[tr.tolist(), va.tolist()] for tr, va in folds], separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        bank = compact_bank(p=X_train.shape[1])
        op_names = [operator.name for operator in bank]
        score_sum = np.zeros((len(bank), k_max), dtype=float)
        score_n = np.zeros((len(bank), k_max), dtype=int)
        captured_warnings: list[str] = []
        for train_idx, valid_idx in folds:
            X_fold, X_valid = X_train[train_idx], X_train[valid_idx]
            y_fold, y_valid = y_train[train_idx], y_train[valid_idx]
            for op_index in range(len(bank)):
                try:
                    result, T_fold, T_valid = _fit_latent(
                        X_fold, y_fold, X_valid, classes, bank, op_index, k_max
                    )
                    available = min(result.n_components, T_fold.shape[1], T_valid.shape[1])
                    for k in range(1, available + 1):
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter("always", ConvergenceWarning)
                            calibrator = _fit_calibrator(T_fold[:, :k], y_fold, seed)
                        captured_warnings.extend(str(item.message) for item in caught)
                        proba = _align_proba(
                            calibrator.predict_proba(T_valid[:, :k]),
                            calibrator.classes_, len(classes),
                        )
                        score_sum[op_index, k - 1] += _balanced_log_loss(y_valid, proba)
                        score_n[op_index, k - 1] += 1
                except Exception as exc:
                    captured_warnings.append(f"op={op_names[op_index]} fold failed: {exc}")
        scores = np.full_like(score_sum, np.inf)
        valid = score_n == n_splits
        scores[valid] = score_sum[valid] / score_n[valid]
        if not np.isfinite(scores[0]).any():
            raise RuntimeError("identity candidate has no finite CV score")
        selections = {
            METHOD_IDENTITY: (0, int(np.nanargmin(scores[0]))),
            METHOD_AOM: tuple(int(value) for value in np.unravel_index(np.argmin(scores), scores.shape)),
        }
        test_hashes = _row_hashes(X_test)
        _, unique_test_indices = np.unique(test_hashes, return_index=True)
        unique_test_indices = np.sort(unique_test_indices)
        file_hashes = {key: _sha256(path) for key, path in paths.items()}
        split_files = {key: str(path) for key, path in paths.items()}
        output: list[dict[str, Any]] = []
        for method, (op_index, k_index) in selections.items():
            selected_k = k_index + 1
            result, T_train, T_test = _fit_latent(
                X_train, y_train, X_test, classes, bank, op_index, k_max
            )
            if selected_k > result.n_components:
                raise RuntimeError(
                    f"selected k={selected_k} exceeds final components={result.n_components}"
                )
            calibrator = _fit_calibrator(T_train[:, :selected_k], y_train, seed)
            fit_select_time = time.perf_counter() - started
            predict_start = time.perf_counter()
            proba = _align_proba(
                calibrator.predict_proba(T_test[:, :selected_k]),
                calibrator.classes_, len(classes),
            )
            pred = np.argmax(proba, axis=1)
            predict_time = time.perf_counter() - predict_start
            unique_y = y_test[unique_test_indices]
            unique_proba = proba[unique_test_indices]
            unique_pred = pred[unique_test_indices]
            output.append({
                "protocol_id": PROTOCOL_ID,
                "database_name": row["database_name"], "dataset": row["dataset"],
                "seed": seed, "method": method, "status": "ok", "status_details": "",
                "n_train": len(X_train), "n_test": len(X_test), "n_features": X_train.shape[1],
                "n_classes": len(classes),
                "class_counts_train_json": json.dumps(np.bincount(y_train).tolist()),
                "class_counts_test_json": json.dumps(np.bincount(y_test, minlength=len(classes)).tolist()),
                "external_split_files_json": json.dumps(split_files, sort_keys=True),
                "fold_hash": fold_hash, "cv_folds": n_splits,
                "k_grid": json.dumps(k_grid),
                "candidate_operators": 1 if method == METHOD_IDENTITY else len(bank),
                "selected_operator_index": op_index, "selected_operator": op_names[op_index],
                "selected_k": selected_k,
                "cv_balanced_log_loss": float(scores[op_index, k_index]),
                "balanced_accuracy": balanced_accuracy(y_test, pred),
                "macro_f1": macro_f1(y_test, pred),
                "log_loss": log_loss(y_test, proba, classes=classes),
                "ece_10_equal_width": expected_calibration_error(y_test, proba, n_bins=10),
                "n_unique_test_spectra": len(unique_test_indices),
                "duplicate_test_excess": len(X_test) - len(unique_test_indices),
                "balanced_accuracy_unique_test_spectra": balanced_accuracy(unique_y, unique_pred),
                "log_loss_unique_test_spectra": log_loss(unique_y, unique_proba, classes=classes),
                "fit_select_time_s": fit_select_time, "predict_time_s": predict_time,
                "input_sha256_json": json.dumps(file_hashes, sort_keys=True),
                "warnings_json": json.dumps(sorted(set(captured_warnings))),
            })
        return output


def _load_completed(path: Path) -> tuple[list[dict[str, Any]], set[tuple[str, str, int]]]:
    if not path.is_file():
        return [], set()
    frame = pd.read_csv(path)
    if len(frame) and not frame["protocol_id"].eq(PROTOCOL_ID).all():
        raise RuntimeError(f"refusing to resume a different protocol: {path}")
    complete: set[tuple[str, str, int]] = set()
    for key, group in frame.groupby(["database_name", "dataset", "seed"]):
        if set(group["method"]) == {METHOD_IDENTITY, METHOD_AOM} and group["status"].eq("ok").all():
            complete.add((str(key[0]), str(key[1]), int(key[2])))
    return frame.to_dict("records"), complete


def _write_raw(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r["database_name"], r["dataset"], int(r["seed"]), r["method"]))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)


def _bootstrap_median_ci(values: np.ndarray, seed: int = 20260904, n_boot: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(n_boot, len(values)), replace=True)
    medians = np.median(draws, axis=1)
    return tuple(float(x) for x in np.quantile(medians, [0.025, 0.975]))


def _one_summary(task: pd.DataFrame) -> dict[str, Any]:
    """Summarize already seed-averaged paired task rows."""
    delta = task["delta_balanced_accuracy"].to_numpy(dtype=float)
    ci_low, ci_high = _bootstrap_median_ci(delta)
    nonzero = delta[delta != 0]
    wilcox = wilcoxon(
        nonzero, alternative="two-sided", zero_method="wilcox", method="auto"
    ) if len(nonzero) else None
    return {
        "analysis_unit": "task mean across seeds",
        "n_tasks": int(len(task)), "n_source_families": int(task["database_name"].nunique()),
        "median_delta_balanced_accuracy": float(np.median(delta)),
        "bootstrap_95_ci": [ci_low, ci_high], "bootstrap_replicates": 10000,
        "wins": int(np.sum(delta > 0)), "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "wilcoxon_two_sided_p": float(wilcox.pvalue) if wilcox else None,
        "wilcoxon_zero_method": "wilcox",
        "median_identity_balanced_accuracy": float(task["identity_balanced_accuracy"].median()),
        "median_aom_balanced_accuracy": float(task["aom_balanced_accuracy"].median()),
        "median_identity_log_loss": float(task["identity_log_loss"].median()),
        "median_aom_log_loss": float(task["aom_log_loss"].median()),
    }


def _family_summary(task: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    families = task.groupby("database_name", as_index=False).agg(
        n_tasks=("dataset", "size"),
        identity_balanced_accuracy=("identity_balanced_accuracy", "median"),
        aom_balanced_accuracy=("aom_balanced_accuracy", "median"),
        delta_balanced_accuracy=("delta_balanced_accuracy", "median"),
    )
    family_delta = families["delta_balanced_accuracy"].to_numpy(dtype=float)
    non_ties = int(np.sum(family_delta != 0))
    summary = {
        "analysis_unit": "source-family median of task means",
        "n_source_families": int(len(families)),
        "median_delta_balanced_accuracy": float(np.median(family_delta)),
        "wins": int(np.sum(family_delta > 0)), "ties": int(np.sum(family_delta == 0)),
        "losses": int(np.sum(family_delta < 0)),
        "one_sided_sign_p": float(binomtest(
            int(np.sum(family_delta > 0)), non_ties, 0.5, alternative="greater"
        ).pvalue) if non_ties else None,
    }
    return families, summary


def _summarize(raw_path: Path, archive_path: Path, output_dir: Path) -> dict[str, Any]:
    data = pd.read_csv(raw_path)
    ok = data[data["status"] == "ok"].copy()
    keys = ["database_name", "dataset", "seed"]
    wide = ok.pivot(index=keys, columns="method", values=[
        "balanced_accuracy", "macro_f1", "log_loss", "ece_10_equal_width",
        "balanced_accuracy_unique_test_spectra", "log_loss_unique_test_spectra",
        "selected_k", "selected_operator", "cv_balanced_log_loss",
    ])
    if METHOD_IDENTITY not in wide.columns.get_level_values(1) or METHOD_AOM not in wide.columns.get_level_values(1):
        raise RuntimeError("raw results do not contain both matched methods")
    paired = pd.DataFrame(index=wide.index).reset_index()
    for metric in (
        "balanced_accuracy", "macro_f1", "log_loss", "ece_10_equal_width",
        "balanced_accuracy_unique_test_spectra", "log_loss_unique_test_spectra",
        "selected_k", "cv_balanced_log_loss",
    ):
        paired[f"identity_{metric}"] = wide[(metric, METHOD_IDENTITY)].to_numpy()
        paired[f"aom_{metric}"] = wide[(metric, METHOD_AOM)].to_numpy()
    paired["aom_selected_operator"] = wide[("selected_operator", METHOD_AOM)].to_numpy()
    paired["delta_balanced_accuracy"] = paired["aom_balanced_accuracy"] - paired["identity_balanced_accuracy"]
    paired["delta_log_loss"] = paired["aom_log_loss"] - paired["identity_log_loss"]
    paired.to_csv(output_dir / "per_seed_paired_results.csv", index=False)
    numeric = [column for column in paired.columns if column not in {
        "database_name", "dataset", "seed", "aom_selected_operator"
    }]
    task = paired.groupby(["database_name", "dataset"], as_index=False)[numeric].mean()
    task["n_seeds"] = paired.groupby(["database_name", "dataset"]).size().to_numpy()
    selected = paired.groupby(["database_name", "dataset"])["aom_selected_operator"].agg(
        lambda values: json.dumps(pd.Series(values).value_counts().to_dict(), sort_keys=True)
    ).to_numpy()
    task["aom_selected_operator_counts_json"] = selected
    task.to_csv(output_dir / "per_task_results.csv", index=False)
    task_summary = _one_summary(task)
    families, family_summary = _family_summary(task)
    families.to_csv(output_dir / "source_family_results.csv", index=False)
    archive = pd.read_csv(archive_path)
    headline_models = {"PLS-DA-standard", "AOM-PLS-DA-global-simpls-covariance"}
    headline = archive[(archive["status"] == "ok") & archive["model"].isin(headline_models)]
    headline_names = headline.groupby(["database_name", "dataset"])["model"].nunique()
    headline_keys = set(headline_names[headline_names == 2].index.tolist())
    matched_headline = task[
        task.apply(lambda row: (row["database_name"], row["dataset"]) in headline_keys, axis=1)
    ].copy()
    matched_headline.to_csv(output_dir / "per_task_archived_headline_intersection.csv", index=False)
    headline_families, headline_family_summary = _family_summary(matched_headline)
    headline_families.to_csv(output_dir / "source_family_archived_headline_intersection.csv", index=False)
    summary = {
        "all_currently_runnable": task_summary,
        "archived_headline_intersection": _one_summary(matched_headline),
        "source_family_sensitivity_all": family_summary,
        "source_family_sensitivity_archived_headline": headline_family_summary,
    }
    (output_dir / "paired_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([
        {"scope": name, **values} for name, values in summary.items()
    ]).to_csv(output_dir / "paired_summary.csv", index=False)
    return summary


def _audit_archive(archive_path: Path, output_dir: Path) -> dict[str, Any]:
    archive = pd.read_csv(archive_path)
    by = archive.groupby(
        ["model", "engine", "operator_bank", "criterion", "status"], dropna=False
    ).size().rename("rows").reset_index()
    by.to_csv(output_dir / "archived_protocol_counts.csv", index=False)
    ok = archive[archive["status"] == "ok"]
    audit = {
        "path": str(archive_path.resolve()), "rows": int(len(archive)), "ok_rows": int(len(ok)),
        "models": int(archive["model"].nunique()),
        "ok_criterion_values": sorted(ok["criterion"].dropna().astype(str).unique().tolist()),
        "logged_n_splits_values": sorted(float(x) for x in ok["n_splits"].dropna().unique()),
        "holdout_implementation": "legacy 20% split, np.random.RandomState(42), independent of run seed",
        "headline_baseline_engine": "pls_standard with identity-only bank",
        "headline_aom_engine": "simpls_covariance with compact nine-operator bank",
        "finding": "Archived classification selection used holdout, not five-fold CV; n_splits=5 is metadata only for these rows. The headline contrast also changes both operator set and PLS engine.",
    }
    (output_dir / "archived_protocol_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def _audit_inout(data_root: Path, output_dir: Path) -> dict[str, Any]:
    base = data_root / "classification" / "ARABIDOPSIS_CEFE" / "InOut_1264"
    X_train, X_test = _read_x(base / "Xtrain.csv"), _read_x(base / "Xtest.csv")
    y_train, y_test = _read_y(base / "Ytrain.csv"), _read_y(base / "Ytest.csv")
    train_hash, test_hash = _row_hashes(X_train), _row_hashes(X_test)
    train_counts = pd.Series(train_hash).value_counts()
    test_counts = pd.Series(test_hash).value_counts()
    duplicate_groups = test_counts[test_counts > 1]
    conflicting = 0
    for row_hash in duplicate_groups.index:
        if len(np.unique(y_test[test_hash == row_hash])) > 1:
            conflicting += 1
    audit = {
        "dataset": "InOut_1264", "source_family": "ARABIDOPSIS_CEFE",
        "n_train": int(len(X_train)), "n_test": int(len(X_test)), "n_total": int(len(X_train) + len(X_test)),
        "name_implies_n": 1264, "observed_total_differs_from_name_by": int(len(X_train) + len(X_test) - 1264),
        "unique_train_spectra": int(len(train_counts)), "unique_test_spectra": int(len(test_counts)),
        "train_duplicate_excess": int(len(X_train) - len(train_counts)),
        "test_duplicate_excess": int(len(X_test) - len(test_counts)),
        "test_duplicate_groups": int(len(duplicate_groups)),
        "largest_test_duplicate_group": int(duplicate_groups.max()) if len(duplicate_groups) else 1,
        "duplicate_groups_with_conflicting_labels": int(conflicting),
        "exact_train_test_spectral_overlap": int(len(set(train_hash).intersection(set(test_hash)))),
        "train_class_counts": pd.Series(y_train).value_counts().sort_index().to_dict(),
        "test_class_counts": pd.Series(y_test).value_counts().sort_index().to_dict(),
        "group_metadata_files_present": sorted(path.name for path in base.glob("M*.csv")),
        "cohort_split_type": "unspecified",
        "provenance_conclusion": "No sample/group identifiers accompany X/Y; group leakage cannot be audited. Exact duplicates occur only within the test split, not across train/test.",
    }
    (output_dir / "inout_duplicate_group_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def _write_report(
    output_dir: Path,
    archive: dict[str, Any],
    inout: dict[str, Any],
    summary: dict[str, Any],
    failures: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    task = summary["archived_headline_intersection"]
    all_task = summary["all_currently_runnable"]
    family = summary["source_family_sensitivity_archived_headline"]
    report = f"""# Matched PLS-DA reviewer control

## Protocol

- Protocol ID: `{PROTOCOL_ID}`.
- External train/test files are preserved exactly; labels are learned from training only.
- Both arms use fold-local class-balanced one-hot coding `1/sqrt(training-fold prior)`, covariance-SIMPLS, logistic regression (`class_weight=balanced`, `lbfgs`, `max_iter=2000`), the same stratified {args.cv}-fold partitions for each seed, and `k=1..{args.max_components}`.
- Identity arm searches only identity x k; AOM arm searches the nine compact strict-linear operators x the identical k-grid. Selection minimizes mean class-balanced validation log-loss. Seeds: `{args.seeds}`.
- CPU-only execution: {args.max_workers} worker processes maximum and one BLAS/OpenMP thread per worker.

## Archived-protocol audit

{archive['finding']} The archive has {archive['rows']} rows ({archive['ok_rows']} successful); successful criterion values are {archive['ok_criterion_values']} while `n_splits` is logged as {archive['logged_n_splits_values']}.

## Matched result

On the exact {task['n_tasks']}-task intersection used by the archived headline contrast ({task['n_source_families']} source families), median AOM-minus-identity balanced accuracy is {task['median_delta_balanced_accuracy']:.6f} (task bootstrap 95% CI {task['bootstrap_95_ci'][0]:.6f} to {task['bootstrap_95_ci'][1]:.6f}); wins/ties/losses = {task['wins']}/{task['ties']}/{task['losses']}; two-sided Wilcoxon p = {task['wilcoxon_two_sided_p']:.6g}. Median balanced accuracy is {task['median_identity_balanced_accuracy']:.6f} for identity and {task['median_aom_balanced_accuracy']:.6f} for AOM. Median log-loss is {task['median_identity_log_loss']:.6f} and {task['median_aom_log_loss']:.6f}, respectively.

Source-family sensitivity on that intersection: median delta {family['median_delta_balanced_accuracy']:.6f}, wins/ties/losses {family['wins']}/{family['ties']}/{family['losses']}, one-sided sign p = {family['one_sided_sign_p']:.6g} over {family['n_source_families']} families. Including the now-resolvable `Species_56_Bagnall` task gives N={all_task['n_tasks']}, median delta {all_task['median_delta_balanced_accuracy']:.6f}, wins/ties/losses {all_task['wins']}/{all_task['ties']}/{all_task['losses']}, and two-sided Wilcoxon p={all_task['wilcoxon_two_sided_p']:.6g}.

## Run exclusions

{len(failures)} task-seed jobs failed. These are recorded in `run_failures.csv`; the observed blockers are non-finite spectra in `Group9_1856` and both FUSARIUM classification tasks.

## InOut_1264 audit

The files contain {inout['n_train']} train + {inout['n_test']} test = {inout['n_total']} rows (one fewer than the dataset name). Train has {inout['train_duplicate_excess']} exact duplicate excess; test has {inout['test_duplicate_excess']} excess rows in {inout['test_duplicate_groups']} duplicate groups (largest group {inout['largest_test_duplicate_group']}); {inout['duplicate_groups_with_conflicting_labels']} duplicate groups have conflicting labels. Exact train/test spectral overlap is {inout['exact_train_test_spectral_overlap']}. No `M*.csv` group metadata is present and the cohort split type is `unspecified`, so specimen/group leakage cannot be assessed. Per-run metrics include a sensitivity that collapses exact test-spectrum duplicates.

## Outputs and environment

- `matched_results.csv`: raw method x task x seed results and hashes.
- `per_seed_paired_results.csv`, `per_task_results.csv`: paired results.
- `paired_summary.csv/json`, `source_family_results.csv`: task and family summaries, including the exact archived-headline intersection.
- `archived_protocol_counts.csv/json`: holdout-vs-CV audit.
- `inout_duplicate_group_audit.json`: duplicate/provenance audit.
- Python {platform.python_version()}, NumPy {np.__version__}, SciPy {scipy.__version__}, scikit-learn {sklearn.__version__}, pandas {pd.__version__}.
"""
    (output_dir / "PROTOCOL_REPORT.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=REPO / "benchmarks/pls/cohort_classification.csv")
    parser.add_argument("--data-root", type=Path, default=Path("/home/delete/nirs4all/nirs4all-data"))
    parser.add_argument("--archive", type=Path, default=REPO / "benchmarks/runs/pls/paper_aom_aompls_da_seeds012/results.csv")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "matched_plsda")
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--cv", type=int, default=5)
    parser.add_argument("--max-components", type=int, default=15)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.max_workers < 1 or args.max_workers > 5:
        raise SystemExit("--max-workers must be between 1 and 5 for this reviewer control")
    cpu_count = os.cpu_count() or 1
    if args.max_workers > max(1, cpu_count - 2):
        raise SystemExit("worker count must leave at least two logical CPUs free")
    seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    cohort = pd.read_csv(args.cohort)
    if args.limit:
        cohort = cohort.head(args.limit)
    raw_path = args.output_dir / "matched_results.csv"
    rows, completed = _load_completed(raw_path)
    failures: list[dict[str, Any]] = []
    jobs = []
    for row in cohort.to_dict("records"):
        try:
            paths = _resolve_split(row, args.data_root)
        except FileNotFoundError as exc:
            print(f"SKIP {row['database_name']}/{row['dataset']}: {exc}", file=sys.stderr)
            continue
        for seed in seeds:
            key = (str(row["database_name"]), str(row["dataset"]), seed)
            if key not in completed:
                jobs.append({
                    "row": row, "seed": seed, "paths": {k: str(v) for k, v in paths.items()},
                    "cv": args.cv, "max_components": args.max_components,
                })
    print(f"protocol={PROTOCOL_ID} jobs={len(jobs)} already_complete={len(completed)} workers={args.max_workers}")
    if jobs:
        with ProcessPoolExecutor(max_workers=args.max_workers) as pool:
            futures = {pool.submit(_evaluate_job, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    new_rows = future.result()
                except Exception as exc:
                    print(f"ERROR {job['row']['database_name']}/{job['row']['dataset']} seed={job['seed']}: {exc}", file=sys.stderr)
                    failures.append({
                        "database_name": job["row"]["database_name"],
                        "dataset": job["row"]["dataset"], "seed": job["seed"],
                        "error": str(exc),
                    })
                    continue
                rows.extend(new_rows)
                _write_raw(raw_path, rows)
                print(f"OK {job['row']['database_name']}/{job['row']['dataset']} seed={job['seed']}", flush=True)
    archive = _audit_archive(args.archive, args.output_dir)
    inout = _audit_inout(args.data_root, args.output_dir)
    pd.DataFrame(
        failures, columns=["database_name", "dataset", "seed", "error"]
    ).to_csv(args.output_dir / "run_failures.csv", index=False)
    if not raw_path.is_file():
        raise SystemExit("no matched jobs completed; see errors above")
    summary = _summarize(raw_path, args.archive, args.output_dir)
    args.seeds = ",".join(str(value) for value in seeds)
    _write_report(args.output_dir, archive, inout, summary, failures, args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
