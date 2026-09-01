# Bundled nirs4all synthetic examples

The three bundled examples are realistic synthetic spectra, not the datasets
used for the paper benchmark. Each keeps the standard separate-file contract:
`Xcal.csv`, `Ycal.csv`, `Xval.csv`, and `Yval.csv`.

`generate_demo_datasets.py` calls `nirs4all.synthesis.SyntheticNIRSGenerator`
from commit `b4b04b8f49cf47cf9ae9b94017ab53c694cdf0d4`. Each recipe creates 120 spectra
(90 calibration, 30 validation) on 301 wavelengths from 1000 to 2500 nm. The
examples cover realistic food composition, grain starch, and a four-batch
process. See `manifest.json` for metadata and immutable source
links. The source repository is licensed under AGPL-3.0-or-later.

Run `../sync_datasets.sh` to regenerate these files from a sibling `nirs4all`
checkout. Update the manifest commit and verify the page whenever the generator
snapshot changes.
