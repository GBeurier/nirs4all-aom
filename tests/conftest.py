"""Shared pytest configuration for the aom_nirs test suite.

Common fixtures here are visible to every subpackage (`tests/pls/`,
`tests/ridge/`, `tests/fast/`). Per-subpackage `conftest.py` files
provide additional fixtures specific to their tests.
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(scope="session")
def rng():
    """Session-wide seeded numpy generator (seed 0)."""
    return np.random.default_rng(0)


@pytest.fixture
def synthetic_nir_regression():
    """Small NIR-like regression dataset.

    Returns (X, y) with smooth row spectra of shape (60, 200) and a
    target that depends linearly on a few wavelength regions.
    """
    rng = np.random.default_rng(42)
    n, p = 60, 200
    X = rng.standard_normal((n, p))
    # Light smoothing along the wavelength axis to mimic real NIR.
    kernel = np.array([0.25, 0.5, 0.25])
    X = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="same"), axis=1, arr=X
    )
    beta = np.zeros(p)
    beta[30:50] = 1.0
    beta[100:120] = 0.5
    y = X @ beta + 0.1 * rng.standard_normal(n)
    return X, y


@pytest.fixture
def synthetic_nir_classification():
    """Small NIR-like classification dataset (binary)."""
    rng = np.random.default_rng(123)
    n, p = 80, 200
    X = rng.standard_normal((n, p))
    kernel = np.array([0.25, 0.5, 0.25])
    X = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="same"), axis=1, arr=X
    )
    beta = np.zeros(p)
    beta[30:50] = 1.0
    z = X @ beta + 0.5 * rng.standard_normal(n)
    y = (z > np.median(z)).astype(int)
    return X, y
