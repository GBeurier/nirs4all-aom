"""AOM panoply with explicit user CV splitters.

Compares PLS, AOM-PLS, AOM-Ridge, AOMRidgeAutoSelector, AOMRidgeBlender,
and FastAOM on one synthetic NIR-like dataset. The same user-defined splitters
are passed to the AOM estimators that perform internal validation.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]


def _load_aom_models():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from aom_nirs.fast import FastAOMConfig, FastAOMPLSRidge
    from aom_nirs.pls import AOMPLSRegressor
    from aom_nirs.ridge import AOMRidgeAutoSelector, AOMRidgeBlender, AOMRidgeRegressor

    return (
        FastAOMConfig,
        FastAOMPLSRidge,
        AOMPLSRegressor,
        AOMRidgeAutoSelector,
        AOMRidgeBlender,
        AOMRidgeRegressor,
    )


(
    FastAOMConfig,
    FastAOMPLSRidge,
    AOMPLSRegressor,
    AOMRidgeAutoSelector,
    AOMRidgeBlender,
    AOMRidgeRegressor,
) = _load_aom_models()


def make_synthetic_nir(
    n_samples: int = 72,
    n_features: int = 180,
    n_active: int = 6,
    noise: float = 0.04,
    random_state: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth spectra with baseline drift, scatter, and sparse target signal."""
    rng = np.random.default_rng(random_state)
    wavelengths = np.linspace(900.0, 1700.0, n_features)
    centers = rng.uniform(950.0, 1650.0, size=4)
    widths = rng.uniform(15.0, 80.0, size=4)
    bands = np.stack(
        [np.exp(-((wavelengths - c) ** 2) / (w**2)) for c, w in zip(centers, widths)],
        axis=0,
    )
    concentrations = rng.standard_normal((n_samples, 4))
    X = concentrations @ bands
    t = np.linspace(-1.0, 1.0, n_features)
    drift = rng.standard_normal((n_samples, 3)) @ np.stack([np.ones_like(t), t, t**2], axis=0)
    scatter = 1.0 + 0.05 * rng.standard_normal(n_samples)
    X = (X + 0.35 * drift) * scatter[:, None]
    X = X + noise * rng.standard_normal(X.shape)
    active_idx = rng.choice(n_features, size=n_active, replace=False)
    coefs = rng.standard_normal(n_active)
    y = X[:, active_idx] @ coefs + 0.02 * rng.standard_normal(n_samples)
    return X, y


QUICK_AOM_RIDGE_CANDIDATES = [
    {
        "label": "Ridge-identity",
        "selection": "superblock",
        "operator_bank": "identity",
        "block_scaling": "none",
        "extra": {"alpha_grid_size": 8, "max_grid_expansions": 0},
    },
    {
        "label": "AOMRidge-global-compact",
        "selection": "global",
        "operator_bank": "compact",
        "block_scaling": "none",
        "extra": {"alpha_grid_size": 8, "max_grid_expansions": 0},
    },
    {
        "label": "AOMRidge-global-compact-snv",
        "selection": "global",
        "operator_bank": "compact",
        "block_scaling": "none",
        "branch_preproc": "snv",
        "extra": {"alpha_grid_size": 8, "max_grid_expansions": 0},
    },
]


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(np.asarray(y_true).ravel(), np.asarray(y_pred).ravel())))


def _evaluate(label: str, make_model, X_train, y_train, X_test, y_test) -> dict[str, object]:
    t0 = time.perf_counter()
    model = make_model()
    model.fit(X_train, y_train)
    fit_time = time.perf_counter() - t0
    y_pred = model.predict(X_test)
    out: dict[str, object] = {
        "label": label,
        "rmse": _rmse(y_test, y_pred),
        "fit_time": fit_time,
        "model": model,
    }
    get_diag = getattr(model, "get_diagnostics", None)
    if callable(get_diag):
        out["diagnostics"] = get_diag()
    elif hasattr(model, "diagnostics_"):
        out["diagnostics"] = model.diagnostics_
    return out


def main() -> None:
    X, y = make_synthetic_nir(random_state=0)
    n_train = 54
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    outer_cv = KFold(n_splits=3, shuffle=True, random_state=0)
    inner_cv = KFold(n_splits=3, shuffle=True, random_state=1)

    results = [
        _evaluate(
            "PLS-10",
            lambda: PLSRegression(n_components=10, scale=False),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
        _evaluate(
            "AOM-PLS compact",
            lambda: AOMPLSRegressor(
                n_components="auto",
                max_components=10,
                operator_bank="compact",
                criterion="cv",
                cv=inner_cv.get_n_splits(),
                cv_splitter=inner_cv,
                random_state=0,
            ),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
        _evaluate(
            "AOM-Ridge global",
            lambda: AOMRidgeRegressor(
                selection="global",
                operator_bank="compact",
                block_scaling="none",
                cv=inner_cv,
                alpha_grid_size=8,
                max_grid_expansions=0,
                random_state=0,
            ),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
        _evaluate(
            "AOM-Ridge auto",
            lambda: AOMRidgeAutoSelector(
                candidates=QUICK_AOM_RIDGE_CANDIDATES,
                outer_cv=outer_cv,
                inner_cv=inner_cv,
                outer_cv_kind="kfold",
                random_state=0,
                n_jobs=1,
            ),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
        _evaluate(
            "AOM-Ridge blender",
            lambda: AOMRidgeBlender(
                candidates=QUICK_AOM_RIDGE_CANDIDATES,
                outer_cv=outer_cv,
                inner_cv=inner_cv,
                outer_cv_kind="kfold",
                regularizer=0.01,
                random_state=0,
                n_jobs=1,
            ),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
        _evaluate(
            "FastAOM sparse",
            lambda: FastAOMPLSRidge(
                config=FastAOMConfig(
                    model="sparse_chains",
                    primitive_bank="compact",
                    max_chain_depth=2,
                    top_global=24,
                    sparse_chains_max_chains=4,
                    random_state=0,
                )
            ),
            X_train,
            y_train,
            X_test,
            y_test,
        ),
    ]

    print("\nAOM panoply on synthetic NIR data")
    print("=" * 72)
    print(f"| {'Model':<22s} | {'RMSE':>8s} | {'Fit (s)':>8s} | {'Diagnostic':<24s} |")
    print(f"|{'-' * 24}|{'-' * 10}|{'-' * 10}|{'-' * 26}|")
    for row in sorted(results, key=lambda item: float(item["rmse"])):
        diag = row.get("diagnostics")
        diagnostic = ""
        if isinstance(diag, dict):
            diagnostic = str(diag.get("selected_variant_label") or diag.get("model") or "")[:24]
        print(
            f"| {str(row['label']):<22s} | {float(row['rmse']):>8.4f} | "
            f"{float(row['fit_time']):>8.2f} | {diagnostic:<24s} |"
        )
    print("=" * 72)
    print("AOM-PLS uses cv_splitter=inner_cv; AOM-Ridge aggregators use outer_cv and inner_cv.")


if __name__ == "__main__":
    main()
