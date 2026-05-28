# Publishing checklist

This document walks through releasing `aompls` to the public package indices
that matter for a scientific library: **PyPI** (Python), **CRAN** (R), and
the optional **conda-forge**, **npm**, **Julia General**, and **MATLAB
File Exchange** channels.

Before any release, bump the version in:

- `cpp/include/aompls/aom_pls.hpp` (if you keep a `#define AOMPLS_VERSION`),
- `python/pyproject.toml` (`[project] version = ...`),
- `python/src/aompls/__init__.py` (`__version__`),
- `r/aompls/DESCRIPTION` (`Version:`),
- `julia/AompLS/Project.toml` (`version = ...`),
- `js/package.json` (`"version": ...`),
- `CHANGELOG.md` (add a new section).

Run the full parity gate locally before tagging:

```bash
./scripts/sync_headers.sh
cd cpp && g++ -std=c++17 -O3 -DEIGEN_NO_DEBUG -DEIGEN_DONT_PARALLELIZE \
    -I include tests/test_parity_kfold.cpp -o build/test_parity_kfold
./build/test_parity_kfold tests/reference

cd ../python && pip install -e . && pytest tests/

cd .. && R CMD build r/aompls && R CMD INSTALL aompls_0.1.0.tar.gz
AOMPLS_REF_DIR=$(pwd)/cpp/tests/reference \
    Rscript -e 'library(aompls); library(testthat); test_dir("r/aompls/tests/testthat")'
```

All three must report PASS. Then tag:

```bash
git tag -a v0.1.0 -m "v0.1.0 — initial release"
git push origin main --tags
```

---

## 1. PyPI (Python)

**Prerequisites** (one-off):

```bash
pip install --upgrade build twine
# Register accounts on https://test.pypi.org and https://pypi.org, then:
#   ~/.pypirc with [pypi] and [testpypi] API tokens — see twine docs.
```

**Build wheels and sdist** from the `python/` directory:

```bash
cd python
rm -rf dist build src/*.egg-info
python -m build           # produces dist/aompls-0.1.0.tar.gz + a wheel
```

The wheel is platform-specific (Linux / macOS / Windows + Python ABI tag).
To publish multi-platform wheels:

- Use **cibuildwheel** in GitHub Actions (recommended). A minimal workflow is
  in `.github/workflows/wheels.yml` (see the template at the end of this file).
- Or build per-platform locally and upload all of them.

**Upload to TestPyPI first** to validate the package metadata:

```bash
python -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ aompls
python -c "from aompls import AOMPLSCompact; print('TestPyPI OK')"
```

**Upload to PyPI**:

```bash
python -m twine upload dist/*
```

**Post-release sanity check**:

```bash
pip install aompls
python -c "import aompls, numpy as np; X = np.random.rand(50, 30); y = np.random.rand(50)
m = aompls.AOMPLSCompact(max_components=5).fit(X, y); print(m.selected_operator_name_)"
```

---

## 2. CRAN (R)

CRAN submissions are reviewed by humans. Plan a few days for the review cycle
on a fresh package.

**Prerequisites** (one-off):

- Read the [CRAN Repository Policy](https://cran.r-project.org/web/packages/policies.html).
- Install `devtools`, `rhub`, `roxygen2`:
  ```r
  install.packages(c("devtools", "rhub", "roxygen2", "spelling"))
  ```

**Pre-flight checks** (from the repo root):

```bash
./scripts/sync_headers.sh   # mirrors cpp headers into r/aompls/inst/include/
R CMD build r/aompls
R CMD check --as-cran aompls_0.1.0.tar.gz
```

`R CMD check --as-cran` MUST report `0 errors, 0 warnings, 0 notes` (a single
NOTE about the "new submission" is acceptable). Common pitfalls:

- **Tarball size**: CRAN rejects tarballs > 5 MB. The vendored Eigen + headers
  add ~7 MB. Use `.Rbuildignore` to keep only the headers the package needs;
  the JSON parity fixtures live under `cpp/tests/reference/` (NOT in
  `r/aompls/`) so they are not in the R tarball. If Eigen still pushes you
  over the limit, vendor only the Eigen submodules you actually use
  (Core, Dense, QR, SVD) instead of the full distribution.
- **No `\dontrun{}` examples** unless absolutely necessary.
- **Examples must run in <5 s each**; use tiny synthetic data.
- **`NEWS.md`** is required for re-submissions; we ship `CHANGELOG.md`,
  rename or symlink as `inst/NEWS.md`.
- **License**: CeCILL-2.1 is recognised by CRAN. The vendored Eigen MPL-2.0
  is added in the DESCRIPTION as `LinkingTo` (not needed since we vendor),
  and disclosed in the LICENSE file.

**Multi-platform test** via [R-hub](https://r-hub.github.io/rhub/):

```r
rhub::check_for_cran(path = "aompls_0.1.0.tar.gz")
```

This runs `R CMD check` on Linux, Windows, and macOS. Address every
warning/note before submitting.

**Submit**: upload at <https://cran.r-project.org/submit.html>. Provide:

- The tarball
- A short email matching `Maintainer:` in DESCRIPTION
- A confirmation that you have read the policies

A CRAN maintainer will reply with either an acceptance or a list of
required fixes. Fix, bump the patch version (e.g. 0.1.0 → 0.1.1), and
re-submit.

**Post-acceptance**:

- Add the `Additional_repositories` line back if you depend on Bioconductor.
- Tag the release on GitHub.
- Update `README.md` install instructions to mention `install.packages("aompls")`.

---

## 3. conda-forge (optional, recommended)

`conda-forge` packages both Python and R libraries with consistent C++ ABIs.

1. Fork <https://github.com/conda-forge/staged-recipes>.
2. Add a new recipe under `recipes/aompls/`:
   - `meta.yaml` with `source.url` pointing at the PyPI sdist, hashed.
   - `build` and `requirements` sections referencing pybind11, numpy.
   - For the R variant, create a separate recipe `r-aompls`.
3. Open a PR. The bot will build on all supported platforms.
4. Once merged, a `conda-forge/aompls-feedstock` repo is created with you as
   maintainer; future releases are bumped via PRs to that feedstock.

A template `recipes/aompls/meta.yaml` is included under
[`packaging/conda-forge.meta.yaml`](packaging/conda-forge.meta.yaml).

---

## 4. npm (JavaScript / WASM)

The `js/` directory ships a WebAssembly build (Emscripten + Embind). Once
`./js/build.sh` produces `dist/aompls.mjs` + `dist/aompls.wasm`:

```bash
cd js
npm publish --access public
```

Make sure `package.json` exposes the dist via `"main"` / `"exports"`:

```json
{
  "main": "dist/aompls.mjs",
  "exports": {
    ".": "./dist/aompls.mjs",
    "./wasm": "./dist/aompls.wasm"
  },
  "files": ["dist", "src", "README.md", "LICENSE"]
}
```

---

## 5. Julia General Registry

1. Fix the UUID in `julia/AompLS/Project.toml` (the placeholder must be
   replaced with a real RFC4122 UUID — generate one with
   `julia -e 'using UUIDs; println(uuid4())'`).
2. Push the package to GitHub at a stable URL.
3. Tag the commit and add a comment:
   ```
   @JuliaRegistrator register subdir=julia/AompLS
   ```
4. JuliaRegistrator opens a PR on the General registry; merge follows
   automatically if CI passes.

---

## 6. MATLAB File Exchange

The MEX wrapper can be shared via the [File Exchange](https://www.mathworks.com/matlabcentral/fileexchange/):

1. Bundle `matlab/aompls_mex.cpp`, `matlab/aom_pls.m`,
   `matlab/aom_pls_predict.m`, `matlab/build.m`, `matlab/test_parity.m`,
   plus the relevant `cpp/include/` headers.
2. Sign in to MATLAB Central, click "Publish a file", upload a zip.
3. Pick category "Statistics and Machine Learning / Regression".
4. Add a brief description and screenshot of `test_parity` output.

---

## 7. Post-release housekeeping

After every release:

1. Push the git tag (`git push origin v0.1.0`).
2. Create a GitHub Release with the CHANGELOG section as the body.
3. Update the parity-gate badge in `README.md`.
4. Open a `vNEXT-dev` milestone for the next cycle.

---

## Appendix: minimal GitHub Actions skeleton (`.github/workflows/release.yml`)

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  python-wheels:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/cibuildwheel@v2.21
        env:
          CIBW_BUILD: "cp39-* cp310-* cp311-* cp312-*"
          CIBW_BEFORE_BUILD: "pip install pybind11"
        with:
          package-dir: python
      - uses: actions/upload-artifact@v4
        with:
          name: wheels-${{ matrix.os }}
          path: wheelhouse/*.whl

  upload-pypi:
    needs: python-wheels
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with: { path: dist, merge-multiple: true }
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}

  r-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: r-lib/actions/setup-r@v2
      - uses: r-lib/actions/setup-r-dependencies@v2
        with:
          working-directory: r/aompls
          extra-packages: any::rcmdcheck
      - run: ./scripts/sync_headers.sh
      - uses: r-lib/actions/check-r-package@v2
        with:
          working-directory: r/aompls
```
