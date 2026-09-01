# Bundled nirs4all dataset snapshots

The three bundled examples are synthetic **format fixtures**, not the datasets
used for the paper benchmark. Each keeps the standard separate-file contract:
`Xcal.csv`, `Ycal.csv`, `Xval.csv`, and `Yval.csv`.

They are copied verbatim from `nirs4all/examples/sample_datasets` at commit
`b4b04b8f49cf47cf9ae9b94017ab53c694cdf0d4`. The generator creates 60
Beer–Lambert-like spectra (48 calibration, 12 validation), 200 spectral
features, baseline variation and noise. See `manifest.json` for per-dataset
metadata and immutable source links. The source repository is licensed under
AGPL-3.0-or-later.

Run `../sync_datasets.sh` to refresh these files from a sibling `nirs4all`
checkout. Update the manifest commit and verify the page whenever snapshots are
refreshed.
