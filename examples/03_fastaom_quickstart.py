"""FastAOM quickstart: sparse multi-kernel Ridge over screened operator chains.

FastAOM enumerates millions of preprocessing chains, screens them with
adjoint-only covariance scores, and fits one of four AOM-style models on the
surviving pool. The ``sparse_mkr`` model is the speed champion in the paper
(FastAOM-sparse-mkr-compact: median ratio 1.022, ~2.5 s per fit). This is
typically a few times faster than the global AOM-PLS CV path in example 01.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
from sklearn.metrics import mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aom_nirs.fast import FastAOMConfig, FastAOMPLSRidge


def make_synthetic_nir(
    n_samples: int = 120,
    n_features: int = 200,
    n_active: int = 5,
    noise: float = 0.05,
    random_state: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth NIR-like spectra with a sparse linear target dependence."""
    rng = np.random.default_rng(random_state)
    wavelengths = np.linspace(900.0, 1700.0, n_features)
    centers = rng.uniform(950.0, 1650.0, size=3)
    widths = rng.uniform(20.0, 80.0, size=3)
    bands = np.stack(
        [np.exp(-((wavelengths - c) ** 2) / (w**2)) for c, w in zip(centers, widths)],
        axis=0,
    )
    concentrations = rng.standard_normal((n_samples, 3))
    X = concentrations @ bands
    t = np.linspace(-1.0, 1.0, n_features)
    drift = rng.standard_normal((n_samples, 2)) @ np.stack([t, t**2], axis=0)
    X = X + 0.3 * drift
    X = X + noise * rng.standard_normal(X.shape)
    active_idx = rng.choice(n_features, size=n_active, replace=False)
    coefs = rng.standard_normal(n_active)
    y = X[:, active_idx] @ coefs + 0.02 * rng.standard_normal(n_samples)
    return X, y


def main() -> None:
    X, y = make_synthetic_nir(random_state=0)
    n_train = 90
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    # FastAOM-sparse-mkr-compact: sparse_mkr model over the compact primitive bank.
    cfg = FastAOMConfig(
        model="sparse_mkr",
        primitive_bank="compact",
        max_chain_depth=3,
        top_global=60,
        sparse_mkr_max_chains=8,
        random_state=0,
    )
    model = FastAOMPLSRidge(config=cfg)

    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    fit_time = time.perf_counter() - t0

    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    diag = model.diagnostics_
    print(f"FastAOM ({cfg.model}, {cfg.primitive_bank}) test RMSE: {rmse:.4f}")
    print(f"Fit time:               {fit_time:.2f} s")
    print(f"Chains enumerated:      {diag['n_chains_enumerated']}")
    print(f"Screened candidates:    {diag['n_candidates_total']}")
    print(f"Finalists kept:         {diag['n_finalists']}")
    print("Note: FastAOM trades a small accuracy hit vs example 01 for a large speed-up.")


if __name__ == "__main__":
    main()
