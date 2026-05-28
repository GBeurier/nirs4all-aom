# aompls — Python binding

Python bindings (via pybind11) for the **aompls** AOM-PLS compact (PLS1)
algorithm. The C++ core is header-only and ships with the package.

## Install

```bash
pip install aompls
```

## Quick start

```python
import numpy as np
from aompls import AOMPLSCompact, tune

X = np.random.rand(200, 256)
y = np.random.rand(200)

# sklearn-compatible estimator
m = AOMPLSCompact(
    max_components=15,
    n_folds=5,
    cv_mode="kfold",          # or "spxy", "holdout", "external"
    one_se_rule=False,
    preproc="none",           # "snv", "msc", "osc", "asls", "snv+osc", "asls+osc"
).fit(X, y)

print(m.selected_operator_name_, m.n_components_)
y_pred = m.predict(X)

# Grid-search HPO (outer K-fold over max_components × preproc)
result = tune(X, y,
              max_components_grid=(5, 10, 15, 20),
              preproc_grid=("none", "snv", "osc"))
print(result.best_params, result.best_score)
```

## Algorithm

- 9-operator compact bank: identity, Savitzky-Golay smoothing (w=11,21),
  Savitzky-Golay derivatives 1 and 2, polynomial detrend (deg 1, 2),
  finite difference.
- Materialised SIMPLS through the chosen operator with auto-prefix
  cross-validation scoring and optional one-standard-error parsimony.
- Optional preprocessing: SNV, MSC, OSC (Wold 1998), ASLS (Eilers-Boelens 2005).

## Repository

Full source, R / MATLAB / Julia / JS bindings, and parity gates:
<https://github.com/GBeurier/aompls>

## License

CeCILL-2.1. Bundles a vendored copy of Eigen 3.4 (MPL-2.0).
