# AOM Panoply and User Splitters

The AOM package exposes three practical layers:

| Layer | Estimator | Recommended Use |
|-------|-----------|-----------------|
| PLS | `AOMPLSRegressor` | PLS-compatible operator-bank selection |
| Ridge | `AOMRidgeRegressor` | Fast single AOM-Ridge model |
| Aggregators | `AOMRidgeAutoSelector`, `AOMRidgeBlender` | Select or blend several AOM-Ridge variants |
| Fast screening | `FastAOMPLSRidge` | Faster chain-screened calibration |

Run the complete user example:

```bash
python examples/04_aom_panoply.py
```

## Explicit CV Splitters

Pass the user splitter directly to the estimators that perform internal
validation:

```python
from sklearn.model_selection import KFold
from aom_nirs.pls import AOMPLSRegressor
from aom_nirs.ridge import AOMRidgeBlender

inner_cv = KFold(n_splits=5, shuffle=True, random_state=0)
outer_cv = KFold(n_splits=5, shuffle=True, random_state=1)

aom_pls = AOMPLSRegressor(
    operator_bank="compact",
    criterion="cv",
    cv=inner_cv.get_n_splits(),
    cv_splitter=inner_cv,
)

blender = AOMRidgeBlender(
    outer_cv=outer_cv,
    inner_cv=inner_cv,
    random_state=0,
)
```

`AOMRidgeAutoSelector` and `AOMRidgeBlender` now expose both `outer_cv` and
`inner_cv`. When a splitter object exposes `for_training_subset(train_idx)`,
the aggregators derive candidate-local inner folds inside each outer-training
slice. This supports precomputed fold protocols from host frameworks such as
nirs4all while keeping candidate validation rows out of candidate training.

## Practical Candidate Set

The full Blender default uses the benchmark HEADLINE variants. For quick user
smokes, pass a smaller list:

```python
candidates = [
    {
        "label": "Ridge-identity",
        "selection": "superblock",
        "operator_bank": "identity",
        "block_scaling": "none",
    },
    {
        "label": "AOMRidge-global-compact",
        "selection": "global",
        "operator_bank": "compact",
        "block_scaling": "none",
    },
    {
        "label": "AOMRidge-global-compact-snv",
        "selection": "global",
        "operator_bank": "compact",
        "block_scaling": "none",
        "branch_preproc": "snv",
    },
]
```

For final benchmark runs, omit `candidates` to use the full default set.
