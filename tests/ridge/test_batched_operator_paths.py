"""Independent operator, cross-kernel and prediction checks for batched adjoints."""

import numpy as np
import pytest
from sklearn.linear_model import Ridge

from aom_nirs.pls.banks import bank_by_name
from aom_nirs.pls.operator_generation import FixedShiftOperator
from aom_nirs.pls.operators import ComposedOperator, LinearSpectralOperator
from aom_nirs.ridge.kernels import linear_operator_kernel_train
from aom_nirs.ridge.solvers import solve_dual_ridge_path_eigh


@pytest.mark.parametrize("p", [7, 33, 64])
def test_all_final_operators_adjoint_matrix_and_cross_prediction(p):
    rng = np.random.default_rng(72 + p)
    X = rng.normal(size=(11, p))
    X -= X.mean(axis=0)
    left = rng.normal(size=(5, p))
    y = rng.normal(size=11)
    y -= y.mean()
    bank = bank_by_name("compact_no_fd_gaussian", p=p)
    operators = bank + [ComposedOperator([bank[3], bank[-1], bank[6]])]
    alphas = np.array([1e-3, 0.2, 100.0])
    for op in operators:
        op.fit(X)
        matrix = op.matrix(p)
        values = rng.normal(size=(p, 8))[:, ::2]
        np.testing.assert_allclose(op.adjoint_vec(values), matrix.T @ values, atol=2e-12)
        assert op.adjoint_vec(np.empty((p, 0))).shape == (p, 0)
        K, U = linear_operator_kernel_train(X, [op], np.ones(1))
        Z = X @ matrix.T
        Zleft = left @ matrix.T
        np.testing.assert_allclose(K, Z @ Z.T, rtol=2e-12, atol=2e-12)
        np.testing.assert_allclose(left @ U, Zleft @ Z.T, rtol=2e-12, atol=2e-12)
        duals = solve_dual_ridge_path_eigh(K, y, alphas)
        for alpha, dual in zip(alphas, duals, strict=True):
            reference = Ridge(alpha=alpha, fit_intercept=False, solver="svd").fit(Z, y)
            folded_prediction = left @ (U @ dual)
            np.testing.assert_allclose(
                folded_prediction,
                reference.predict(Zleft),
                rtol=2e-7,
                atol=2e-8,
                err_msg=f"{op.name}, alpha={alpha}, p={p}",
            )


def test_custom_vector_only_operator_keeps_fallback():
    class VectorOnly(LinearSpectralOperator):
        def _adjoint_vec_impl(self, values):
            assert values.ndim == 1
            return 2 * values

    values = np.arange(15.0).reshape(5, 3)
    np.testing.assert_array_equal(VectorOnly("custom", p=5).adjoint_vec(values), 2 * values)


@pytest.mark.parametrize("shift", [-3, 0, 2])
def test_shift_batched_adjoint(shift):
    op = FixedShiftOperator(shift=shift, p=11)
    values = np.arange(44.0).reshape(11, 4)
    np.testing.assert_array_equal(op.adjoint_vec(values), op.matrix(11).T @ values)


def test_vector_override_on_specialized_operator_keeps_column_semantics():
    from aom_nirs.pls.operators import SavitzkyGolayOperator

    class ScaledAdjoint(SavitzkyGolayOperator):
        def _adjoint_vec_impl(self, values):
            assert values.ndim == 1
            return 2 * super()._adjoint_vec_impl(values)

    op = ScaledAdjoint(window_length=5, polyorder=2, p=11)
    values = np.arange(44.0).reshape(11, 4)
    expected = np.column_stack([op.adjoint_vec(col) for col in values.T])
    np.testing.assert_allclose(op.adjoint_vec(values), expected)
    assert op.adjoint_vec(np.empty((11, 0))).shape == (11, 0)
