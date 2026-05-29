"""Five-minute synthetic reproduction of the paper's main claims on one dataset.

This script compares six calibrations on a single synthetic NIR-like dataset:

  1. PLS-default         -- sklearn ``PLSRegression`` (baseline).
  2. AOM-PLS-simple      -- ``AOMPLSRegressor`` with the compact bank.
  3. AOM-PLS-best        -- ``ASLSBaseline`` -> ``AOMPLSRegressor``.
  4. AOM-Ridge-global    -- ``AOMRidgeRegressor(selection="global")``.
  5. AOM-Ridge-Blender   -- ``AOMRidgeBlender()`` (paper's best result).
  6. FastAOM-sparse-mkr  -- ``FastAOMPLSRidge(model="sparse_chains")``.

This is a *synthetic* smoke. The numerical claims of the paper hold on the
32-NIRS-dataset benchmark cohort; a real reproduction needs those datasets and
the runners in ``benchmarks/`` (see the paper supplement for the cohort and the
runner CLI). The synthetic spectra here are smooth Gaussian-band mixtures with
baseline drift and a sparse linear target, which is enough to exercise every
estimator but not to recover the cohort-level effect sizes.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aom_nirs.fast import FastAOMConfig, FastAOMPLSRidge
from aom_nirs.pls import AOMPLSRegressor
from aom_nirs.pls.preprocessing import ASLSBaseline
from aom_nirs.ridge import AOMRidgeBlender, AOMRidgeRegressor


def make_synthetic_nir(
    n_samples: int = 60,
    n_features: int = 300,
    n_active: int = 6,
    noise: float = 0.04,
    random_state: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Shaped like a small NIR dataset: ``n=60``, ``p=300``, sparse target."""
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

    # Baseline drift (low-frequency polynomial trend per sample).
    t = np.linspace(-1.0, 1.0, n_features)
    drift = rng.standard_normal((n_samples, 3)) @ np.stack([np.ones_like(t), t, t**2], axis=0)
    X = X + 0.4 * drift

    # Multiplicative scatter and additive noise.
    scatter = 1.0 + 0.05 * rng.standard_normal(n_samples)
    X = X * scatter[:, None]
    X = X + noise * rng.standard_normal(X.shape)

    # Sparse target: y is a linear combination of a few absorbance channels.
    active_idx = rng.choice(n_features, size=n_active, replace=False)
    coefs = rng.standard_normal(n_active)
    y = X[:, active_idx] @ coefs + 0.02 * rng.standard_normal(n_samples)
    return X, y


def _evaluate(label: str, fit_fn, X_train, y_train, X_test, y_test) -> dict:
    t0 = time.perf_counter()
    model = fit_fn()
    model.fit(X_train, y_train)
    fit_time = time.perf_counter() - t0
    y_pred = np.asarray(model.predict(X_test)).ravel()
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    return {"label": label, "rmse": rmse, "fit_time": fit_time}


def main() -> None:
    X, y = make_synthetic_nir(random_state=0)
    n_train = 45
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    results = []
    results.append(_evaluate(
        "PLS-default (baseline)",
        lambda: PLSRegression(n_components=10, scale=False),
        X_train, y_train, X_test, y_test,
    ))
    results.append(_evaluate(
        "AOM-PLS-simple",
        lambda: AOMPLSRegressor(
            operator_bank="compact", criterion="cv", cv=5, random_state=0,
        ),
        X_train, y_train, X_test, y_test,
    ))

    # AOM-PLS-best: ASLS baseline correction upstream of AOM-PLS.
    def _fit_aom_pls_best():
        from sklearn.pipeline import Pipeline
        return Pipeline([
            ("asls", ASLSBaseline()),
            ("aom_pls", AOMPLSRegressor(
                operator_bank="compact", criterion="cv", cv=5, random_state=0,
            )),
        ])

    results.append(_evaluate(
        "AOM-PLS-best (ASLS -> AOM-PLS)",
        _fit_aom_pls_best,
        X_train, y_train, X_test, y_test,
    ))
    results.append(_evaluate(
        "AOM-Ridge-global",
        lambda: AOMRidgeRegressor(
            selection="global", operator_bank="compact", random_state=0,
        ),
        X_train, y_train, X_test, y_test,
    ))
    results.append(_evaluate(
        "AOM-Ridge-Blender",
        lambda: AOMRidgeBlender(outer_cv=3, random_state=0),
        X_train, y_train, X_test, y_test,
    ))
    results.append(_evaluate(
        "FastAOM-sparse-mkr-compact",
        lambda: FastAOMPLSRidge(config=FastAOMConfig(
            model="sparse_chains", primitive_bank="compact",
            max_chain_depth=3, top_global=60, sparse_chains_max_chains=8,
            random_state=0,
        )),
        X_train, y_train, X_test, y_test,
    ))

    baseline_rmse = results[0]["rmse"]
    print("\nSynthetic paper-smoke results (n=60, p=300, sparse target)")
    print("=" * 70)
    print(f"| {'Model':<32s} | {'RMSE':>8s} | {'Fit (s)':>8s} | {'vs baseline':>11s} |")
    print(f"|{'-' * 34}|{'-' * 10}|{'-' * 10}|{'-' * 13}|")
    for r in results:
        ratio = r["rmse"] / baseline_rmse
        verdict = "WIN" if ratio < 1.0 else ("tie" if abs(ratio - 1.0) < 1e-3 else "loss")
        marker = f"{ratio:.3f} ({verdict})"
        print(f"| {r['label']:<32s} | {r['rmse']:>8.4f} | {r['fit_time']:>8.2f} | {marker:>11s} |")
    print("=" * 70)
    print("Note: the paper's published effect sizes apply to the 32-dataset cohort,")
    print("not to a single synthetic toy. Use benchmarks/ to reproduce the real claims.")


if __name__ == "__main__":
    main()
