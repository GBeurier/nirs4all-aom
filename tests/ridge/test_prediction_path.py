"""Validate CV-only path optimization against independently solved models."""

import numpy as np
import pytest
from sklearn.linear_model import Ridge

from aom_nirs.ridge.solvers import predict_dual_ridge_path_eigh


@pytest.mark.parametrize("shape", [(35, 12), (18, 40)])
@pytest.mark.parametrize("targets", [1, 3])
def test_prediction_path_matches_primal_svd(shape, targets):
    rng = np.random.default_rng(251)
    X = rng.normal(size=shape)
    X[:, -1] = X[:, 0]  # also exercise rank deficiency
    V = rng.normal(size=(9, shape[1]))
    V[:, -1] = V[:, 0]
    y = rng.normal(size=(len(X), targets))
    if targets == 1:
        y = y[:, 0]
    alphas = np.logspace(-3, 4, 50)
    expected = np.stack([Ridge(alpha=a, fit_intercept=False, solver="svd").fit(X, y).predict(V) for a in alphas])
    actual = predict_dual_ridge_path_eigh(X @ X.T, y, alphas, V @ X.T)
    np.testing.assert_allclose(actual, expected, rtol=2e-7, atol=2e-8)


@pytest.mark.parametrize("alphas", [[0], [-1], [np.nan], [np.inf], [[1]]])
def test_invalid_alpha_path(alphas):
    with pytest.raises(ValueError, match="alphas"):
        predict_dual_ridge_path_eigh(np.eye(3), np.ones(3), alphas, np.eye(3))
