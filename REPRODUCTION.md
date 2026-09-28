# Reproducing AOM methods

The Python `aom_nirs` package contains the reference and experimental AOM
implementations. The portable numerical engine and stable production facades
are maintained in `nirs4all-methods`.

Install the research package with `pip install -e '.[bench,dev]'`. Run its
numerical tests with `python -m pytest tests/pls tests/ridge tests/fast` and the
synthetic example with `python examples/paper_smoke.py`.

Manuscripts, supplements, reviewer controls, frozen paper partitions and
publication-specific results are maintained in the private `nirs4all-drafts`
repository until submission. They are not installed with this package.
The paper reproduction bundle will identify exact code, configurations,
partitions and data prerequisites when released.

AOM-PLS, AOM-Ridge, Ridge on PLS scores, ridge-augmented PLS and the FastAOM
variants have distinct contracts. Use explicit operator banks, validation folds
and model settings; a shared family name does not establish numerical parity.
