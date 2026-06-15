"""Regression tests for user-provided inner CV in AOM aggregators."""

from __future__ import annotations

import numpy as np
from aom_nirs.ridge.auto_selector import _dispatch_candidate, _score_candidate, _subset_inner_cv
from aom_nirs.ridge.blender import _oof_predictions_for_candidate
from sklearn.base import BaseEstimator, RegressorMixin


class RecordingSubsetSplitter:
    """Small precomputed splitter with nirs4all-style subset remapping."""

    def __init__(
        self,
        splits: list[tuple[list[int], list[int]]],
        *,
        label: str = "root",
        requests: list[tuple[list[int], str]] | None = None,
    ) -> None:
        self.splits = [
            (np.asarray(train, dtype=int), np.asarray(valid, dtype=int))
            for train, valid in splits
        ]
        self.label = label
        self.requests = [] if requests is None else requests

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return len(self.splits)

    def split(self, X, y=None, groups=None):
        for train, valid in self.splits:
            yield train.copy(), valid.copy()

    def for_training_subset(self, train_idx, label: str | None = None):
        parent_train = np.asarray(train_idx, dtype=int)
        self.requests.append((parent_train.tolist(), label or ""))
        parent_to_local = {int(parent): local for local, parent in enumerate(parent_train)}
        local_splits: list[tuple[list[int], list[int]]] = []
        for train, valid in self.splits:
            local_train = [parent_to_local[int(idx)] for idx in train if int(idx) in parent_to_local]
            local_valid = [parent_to_local[int(idx)] for idx in valid if int(idx) in parent_to_local]
            if local_train and local_valid:
                local_splits.append((local_train, local_valid))
        return RecordingSubsetSplitter(
            local_splits,
            label=label or "subset",
            requests=self.requests,
        )


class MeanRegressor(RegressorMixin, BaseEstimator):
    """Cheap estimator used to exercise aggregator control flow."""

    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(np.asarray(X).shape[0], self.mean_, dtype=float)


def test_dispatch_candidate_passes_splitter_to_aom_pls():
    splitter = RecordingSubsetSplitter([([0, 1, 2], [3, 4, 5])])

    estimator, branch = _dispatch_candidate(
        {
            "label": "AOMPLS",
            "selection": "aom_pls",
            "operator_bank": "compact",
            "extra": {"max_components": 4},
        },
        seed=123,
        inner_cv=splitter,
    )

    assert branch is None
    assert estimator.cv == 1
    assert estimator.cv_splitter is splitter


def test_subset_inner_cv_remaps_parent_indices_to_candidate_local_rows():
    splitter = RecordingSubsetSplitter([([0, 1, 2], [3, 4, 5])])

    subset = _subset_inner_cv(splitter, np.asarray([0, 1, 3, 4], dtype=int))

    assert splitter.requests == [([0, 1, 3, 4], "aom-candidate-inner")]
    [(train, valid)] = list(subset.split(np.zeros((4, 2))))
    np.testing.assert_array_equal(train, np.asarray([0, 1]))
    np.testing.assert_array_equal(valid, np.asarray([2, 3]))


def test_auto_selector_scoring_subsets_user_inner_cv_per_outer_fold():
    X = np.arange(36, dtype=float).reshape(6, 6)
    y = np.linspace(0.0, 1.0, 6)
    splitter = RecordingSubsetSplitter([([0, 1, 2], [3, 4, 5])])
    folds = [
        (np.asarray([0, 1, 3, 4], dtype=int), np.asarray([2, 5], dtype=int)),
    ]

    score, per_fold = _score_candidate(
        {"label": "mean", "factory": MeanRegressor},
        X,
        y,
        folds,
        seed=0,
        scoring="rmse_mean",
        inner_cv=splitter,
    )

    assert np.isfinite(score)
    assert len(per_fold) == 1
    assert splitter.requests == [([0, 1, 3, 4], "aom-candidate-inner")]


def test_blender_oof_subsets_user_inner_cv_per_outer_fold():
    X = np.arange(36, dtype=float).reshape(6, 6)
    y = np.linspace(0.0, 1.0, 6)
    splitter = RecordingSubsetSplitter([([0, 1, 2], [3, 4, 5])])
    folds = [
        (np.asarray([0, 1, 3, 4], dtype=int), np.asarray([2, 5], dtype=int)),
    ]

    oof = _oof_predictions_for_candidate(
        {"label": "mean", "factory": MeanRegressor},
        X,
        y,
        folds,
        seed=0,
        inner_cv=splitter,
    )

    assert oof.shape == y.shape
    assert np.all(np.isfinite(oof))
    assert splitter.requests == [([0, 1, 3, 4], "aom-candidate-inner")]
