# Bundled public NIR examples

The WebAssembly demo bundles compact subsets of three real, openly licensed
EcoSIS datasets from the
[`nirs4all-datasets`](https://github.com/GBeurier/nirs4all-datasets) catalogue.
They are demonstration datasets, not the complete datasets used by the paper's
benchmark. Each keeps the separate-file contract `Xcal.csv`, `Ycal.csv`,
`Xval.csv`, and `Yval.csv`.

| Demo | Source and licence | Response |
|---|---|---|
| Squash glucose | [Cucurbita pepo under two stresses](https://doi.org/10.21232/RLmYbmE3), CC BY | Glucose |
| Crop nitrogen | [Leaf traits of eight crop species](https://doi.org/10.21232/C2GM2Z), ODC-By | Nitrogen (% dry mass) |
| Leaf water stress | [Tabletop leaf dry-downs](https://doi.org/10.21232/egGyynzX), PDDL | Leaf water potential (MPa) |

`generate_demo_datasets.py` first verifies the catalogue's redistribution
clearance, aligns `X.csv` and `Y.csv` by `observation_id`, retains 301 evenly
spaced measured wavelengths from 1000 to 2500 nm, and makes a deterministic
90/30 calibration/validation split. No synthetic spectra or target values are
created. The exact catalogue snapshot is recorded in `manifest.json`.

Run `../sync_datasets.sh` with a sibling `nirs4all-datasets` checkout, or set
`NIRS4ALL_DATASETS_DIR` explicitly. Update the manifest commit and rerun the
page self-test whenever the source snapshot changes.
