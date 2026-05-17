"""AOM-Ridge Blender quickstart: convex non-negative blend of Ridge candidates.

This is the paper's best empirical result on the 32-NIRS-dataset cohort
(median RMSEP ratio 0.918 vs Ridge-default, Wilcoxon Holm-corrected p = 2.6e-4).
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_squared_error

from aom_nirs.ridge import AOMRidgeBlender


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

    # Default candidates: the 8 HEADLINE AOM-Ridge variants.
    model = AOMRidgeBlender(outer_cv=3, random_state=0)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    diag = model.get_diagnostics()
    print(f"AOM-Ridge Blender test RMSE: {rmse:.4f}")
    print(f"Top-weighted candidate:      {diag['selected_variant_label']}")
    print("Convex blend weights (label -> weight):")
    for entry in diag["weight_ranking"]:
        if entry["weight"] > 1e-4:
            print(f"  {entry['label']:<48s} {entry['weight']:.4f}")


if __name__ == "__main__":
    main()
