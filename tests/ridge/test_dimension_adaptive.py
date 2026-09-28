"""Shape-adaptive Ridge preserves full CV surfaces and public fit outputs."""

import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from aom_nirs.pls.banks import bank_by_name
from aom_nirs.ridge import AOMRidgeRegressor, estimators, selection
from aom_nirs.ridge.kernels import explicit_superblock
from aom_nirs.ridge.preprocessing import apply_feature_scaler


@pytest.mark.parametrize("shape", [(84, 25), (30, 41)])
@pytest.mark.parametrize("targets", [1, 2])
@pytest.mark.parametrize("scaling,center", [("none", True), ("rms", True), ("none", False)])
def test_complete_cv_surface_matches_sample_space(monkeypatch, shape, targets, scaling, center):
    rng = np.random.default_rng(2309)
    X = rng.normal(size=shape) + 10 * np.sin(np.linspace(0, 3, shape[1]))
    X[:, -1] = X[:, 0]  # rank-deficient input
    Y = rng.normal(size=(len(X), targets))
    bank = bank_by_name("compact_no_fd_gaussian", p=shape[1])
    args = (X, Y, bank, np.array([1e-3, 1.0, 100.0]), KFold(3, shuffle=True, random_state=91))
    kwargs = {"block_scaling": scaling, "center": center, "return_per_fold": True}
    actual = selection.cv_score_branch_global(*args, **kwargs)
    original = selection._fold_local_kernels

    def force_dual(*args, **kwargs):
        kwargs["primal_if_smaller"] = False
        return original(*args, **kwargs)

    monkeypatch.setattr(selection, "_fold_local_kernels", force_dual)
    expected = selection.cv_score_branch_global(*args, **kwargs)
    for a, b in zip(actual, expected, strict=True):
        np.testing.assert_allclose(a, b, rtol=2e-6, atol=2e-7)
    assert np.argmin(actual[0]) == np.argmin(expected[0])


@pytest.mark.parametrize("selection_mode", ["global", "branch_global", "superblock"])
@pytest.mark.parametrize("solver", ["auto", "eigh"])
@pytest.mark.parametrize("targets", [1, 2])
def test_tall_fit_matches_explicit_svd_without_sample_kernel(monkeypatch, selection_mode, solver, targets):
    rng = np.random.default_rng(2310)
    X = rng.normal(size=(120, 25))
    X[:, -1] = X[:, 0] + 1e-7 * X[:, 1]
    V = rng.normal(size=(11, 25))
    Y = rng.normal(size=(len(X), targets))
    if targets == 1:
        Y = Y[:, 0]
    bank = bank_by_name("compact_no_fd_gaussian", p=25)[:2]

    def forbidden(*args, **kwargs):
        raise AssertionError("a tall fit must not allocate the sample Gram matrix")

    monkeypatch.setattr(selection, "linear_operator_kernel_train", forbidden)
    monkeypatch.setattr(estimators, "linear_operator_kernel_train", forbidden)
    model = AOMRidgeRegressor(
        selection=selection_mode, branches=("snv",), operator_bank=bank,
        alphas="auto", alpha_grid_size=5, adaptive_alpha_grid=False,
        solver=solver, cv=3, block_scaling="rms", x_scale="feature_std",
    ).fit(X, Y)
    assert model.primal_
    assert model.get_diagnostics()["solve_space"] == "primal"
    branch = model._branch_preproc_
    Xb = X if branch is None else branch.transform(X)
    Vb = V if branch is None else branch.transform(V)
    Xc = apply_feature_scaler(Xb, model.x_mean_, model.x_scale_)
    Vc = apply_feature_scaler(Vb, model.x_mean_, model.x_scale_)
    selected = [bank[i].fit(Xc) for i in model.selected_operator_indices_]
    Z = explicit_superblock(Xc, selected, model.block_scales_)
    W = explicit_superblock(Vc, selected, model.block_scales_)
    Y2 = Y.reshape(len(Y), -1)
    ref = Ridge(alpha=model.alpha_, fit_intercept=False, solver="svd").fit(Z, Y2 - model.y_mean_)
    expected = np.asarray(ref.predict(W)).reshape(len(V), -1) + model.y_mean_
    np.testing.assert_allclose(model.predict(V).reshape(len(V), -1), expected, rtol=2e-6, atol=2e-7)
    dual = model.dual_coef_.reshape(len(Y), -1)
    # Check the dual equation without allocating Z @ Z.T.
    np.testing.assert_allclose(Z @ (Z.T @ dual) + model.alpha_ * dual,
                               Y2 - model.y_mean_, rtol=2e-5, atol=2e-6)


def test_primal_path_with_unstable_msc_reference_matches_svd():
    # Noise-only spectra can give near-zero MSC slopes. The old n*n kernel
    # loses precision in this case, so use an independent SVD as the oracle.
    from aom_nirs.ridge.branches import make_branch_preproc
    from aom_nirs.ridge.solvers import predict_dual_ridge_path_eigh

    rng = np.random.default_rng(2309)
    X = rng.normal(size=(84, 25))
    X[:, -1] = X[:, 0]
    Y = rng.normal(size=(84, 2))
    bank = bank_by_name("compact_no_fd_gaussian", p=25)
    alphas = np.array([1e-3, 1.0, 100.0])
    for train, valid in KFold(3, shuffle=True, random_state=91).split(X):
        msc = make_branch_preproc("msc")
        Xt = msc.fit_transform(X[train])
        Xv = msc.transform(X[valid])
        xm, ym = Xt.mean(axis=0), Y[train].mean(axis=0)
        for op in bank:
            A = op.fit(Xt).matrix(25)
            Z, W = (Xt - xm) @ A.T, (Xv - xm) @ A.T
            expected = np.stack([
                Ridge(alpha=a, fit_intercept=False, solver="svd").fit(Z, Y[train] - ym).predict(W)
                for a in alphas
            ])
            actual = predict_dual_ridge_path_eigh(Z.T @ Z, Z.T @ (Y[train] - ym), alphas, W)
            np.testing.assert_allclose(actual, expected, rtol=2e-6, atol=2e-7)


@pytest.mark.parametrize("alpha", [1e-3, 1e-8, 1e-12])
@pytest.mark.parametrize("solver", ["auto", "eigh"])
def test_tall_exact_fit_preserves_dual_equation_at_small_alpha(alpha, solver):
    from aom_nirs.pls.operators import IdentityOperator

    rng = np.random.default_rng(413)
    X = rng.normal(size=(80, 9))
    X -= X.mean(axis=0)
    y = X @ rng.normal(size=9)
    model = AOMRidgeRegressor(
        selection="superblock", operator_bank=[IdentityOperator()],
        alphas=[alpha], adaptive_alpha_grid=False, cv=3,
        block_scaling="none", solver=solver,
    ).fit(X, y)
    reference = Ridge(alpha=alpha, solver="svd").fit(X, y)
    np.testing.assert_allclose(model.predict(X), reference.predict(X), atol=1e-10, rtol=1e-10)
    Xc = X - model.x_mean_
    dual = model.dual_coef_
    np.testing.assert_allclose(
        Xc @ (Xc.T @ dual) + alpha * dual,
        y - model.y_mean_, atol=1e-10, rtol=1e-10,
    )
