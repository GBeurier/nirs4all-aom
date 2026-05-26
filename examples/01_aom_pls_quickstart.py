"""AOM-PLS quickstart: fit on synthetic NIR-like spectra, report RMSE and selected operator."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aom_nirs.pls import AOMPLSRegressor


def make_synthetic_nir(
    n_samples: int = 120,
    n_features: int = 200,
    n_active: int = 5,
    noise: float = 0.05,
    random_state: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth NIR-like spectra with a sparse linear target dependence.

    Each spectrum is a sum of three Gaussian absorbance bands plus a low-frequency
    baseline drift and Gaussian noise. The target ``y`` depends linearly on the
    intensities at ``n_active`` randomly chosen wavelengths.
    """
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

    # Low-frequency baseline drift (per sample, two basis polynomials).
    t = np.linspace(-1.0, 1.0, n_features)
    drift = rng.standard_normal((n_samples, 2)) @ np.stack([t, t**2], axis=0)
    X = X + 0.3 * drift

    # Additive noise.
    X = X + noise * rng.standard_normal(X.shape)

    # Sparse target: y depends on a handful of wavelengths.
    active_idx = rng.choice(n_features, size=n_active, replace=False)
    coefs = rng.standard_normal(n_active)
    y = X[:, active_idx] @ coefs + 0.02 * rng.standard_normal(n_samples)
    return X, y


def main() -> None:
    X, y = make_synthetic_nir(random_state=0)
    n_train = 90
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    model = AOMPLSRegressor(
        n_components="auto",
        max_components=15,
        operator_bank="compact",
        criterion="cv",
        cv=5,
        random_state=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    diag = model.get_diagnostics()
    selected = diag.get("selected_operator_names", model.selected_operators_)

    print(f"AOM-PLS test RMSE: {rmse:.4f}")
    print(f"Components selected: {model.n_components_}")
    print(f"Selected operator(s): {selected}")


if __name__ == "__main__":
    main()
