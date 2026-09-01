# AOM-PLS interactive WebAssembly companion

This self-contained static application turns the AOM paper companion into a
complete, inspectable calibration experiment. In one browser tab it guides a
chemometrician through the following path:

- starts from local, separate `Xcal/Ycal/Xval/Yval` (or train/test) CSV/TSV files;
- offers three traceable `nirs4all` synthetic format fixtures when no local data are available;
- visualizes calibration and held-out spectra plus response distributions;
- keeps the local-file importer visible and reports file-selection/validation errors in place;
- cross-validates the component count of conventional raw-spectrum PLS;
- screens a configurable strict-linear AOM operator bank with the same folds and
  component budget;
- reports the active dataset, raw-PLS CV, AOM screening, held-out scoring, and
  completion stages through a persistent progress indicator;
- compares both routes on the same untouched validation rows; and
- displays the selected operator, transformed spectral view, original-grid
  coefficients, metrics, and measured-versus-predicted values; and
- ends with accessible tabs containing the released PyPI and R-universe install
  commands, executable Python/R examples, and links to both source repositories.

All CSV parsing, native fitting, and prediction stay in the browser. There is no
analytics endpoint and no upload code.

## Run locally

WASM and the bundled CSV files must be served over HTTP:

```bash
python3 -m http.server 8765
# open http://localhost:8765/demo/wasm/
```

Add `?selftest=1` to run the browser parser and fit smoke test. A passing page
sets `data-selftest="pass"` on the root HTML element. A bundled dataset can be
selected directly with `?dataset=B02_wavenumber`, `B03_wavelength`, or
`B04_reflectance`.

The normal page does not launch a fit automatically: it waits for the user to
inspect the active split and click **Compare raw PLS and AOM-PLS**. Self-test
mode runs the comparison automatically.

## Reproducible inputs

The committed JavaScript/WASM bundle is the public `@nirs4all/methods`
**1.0.13** release. Refresh it from the pinned npm version with:

```bash
./stage_bundle.sh
```

The demo uses canonical design tokens, chart styles, and brand marks vendored
unchanged from `nirs4all-ui`. Refresh them from a sibling checkout with:

```bash
./sync_ui_assets.sh
```

The bundled fixtures are verbatim snapshots from `nirs4all`. Refresh them from
a sibling checkout with:

```bash
./sync_datasets.sh
```

If the sibling repositories live elsewhere, set `NIRS4ALL_UI_DIR` or
`NIRS4ALL_DIR`. Dataset provenance and immutable source links live in
`datasets/manifest.json`.

## External file contract

The importer expects four uncompressed text files: calibration X/y and
validation/test X/y. It detects semicolon, comma, tab, and pipe delimiters. X
must be a rectangular numeric matrix and may start with feature labels or
numeric wavelengths/wavenumbers; y must contain one numeric target column with
an optional header. The calibration and validation matrices must have identical
feature counts and numeric axes.

The GitHub Pages workflow publishes only `demo/wasm`.
