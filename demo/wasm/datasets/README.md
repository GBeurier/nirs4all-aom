# Bundled public measured NIR snapshots

The browser demo contains three compact snapshots of public measured datasets,
not synthetic spectra and not the complete paper benchmark. Each uses the same
separate-file contract: `Xcal.csv`, `Ycal.csv`, `Xval.csv`, and `Yval.csv`.

`generate_demo_datasets.py` reads the standardized source files from
`nirs4all-datasets` commit `60a0b6073bd3842bdd0b2e3439ffcbda0ad4615d`.
It performs only documented, deterministic browser reductions:

- **Equine cartilage (CC BY 4.0):** 120 real measurement locations sampled
  deterministically from 869; the replicate spectra at each location are
  averaged, the 700–1050 nm range is retained, and locations are split 90/30.
- **Leaf-litter nitrogen (CC BY 4.0):** 120 real observations sampled
  deterministically from 322 and split 90/30 with the response range spread
  across both partitions; the 1000–2400 nm range is retained.
- **Leaf drydown (PDDL 1.0):** three measured drying stages from each of 48
  leaves. The split is by leaf (36 calibration, 12 validation), so a leaf never
  occurs on both sides; the 1000–2400 nm range is retained.

To keep full browser HPO responsive, cartilage keeps every fourth measured
wavelength and the EcoSIS datasets every eighth measured wavelength within the
stated ranges. No spectra or response values are simulated. Exact sources,
citations, licenses, and transformations are also recorded in `manifest.json`.

Run `./sync_datasets.sh` with a sibling `nirs4all-datasets` checkout, or set
`NIRS4ALL_DATASETS_DIR`, to reproduce the CSV snapshots.
