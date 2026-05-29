# `paper/repro/` — aggregation pipeline for the AOM / Talanta paper

These scripts regenerate the **aggregation tables** of the Talanta manuscript from result CSVs that
are already committed under `benchmarks/runs/` (and the frozen master). **No model is fitted here** —
everything is pure aggregation/statistics over existing scores, so it runs in seconds.

Each script (a) reproduces a known value from `../review/final_stats.md` as a **sanity check** that
its data load + joins are correct, then (b) writes a bare LaTeX `tabularx` fragment that the
manuscript `\input`s. All tables are **scope-clean**: only PLS / Ridge / FastAOM variants — no CNN,
TabPFN, CatBoost, MoE or multi-kernel comparators.

Run everything:

```bash
PYTHON=/path/to/venv/python ./run_all.sh      # needs pandas + numpy + scipy
```

## Script → inputs → output table → manuscript location

| Script | Reads | Writes (fragment) | Used in |
|--------|-------|-------------------|---------|
| `source_family_sensitivity.py` | seeds012 + `ridge/all54_headline` + `linear_hpo .../default_cv5` CSVs; `../review/cohort_manifest.csv` | `table_source_family.tex` | supplement "Source-family clustered sensitivity"; main discussion |
| `hpo_recipe_frequency.py` | `.../paper_aom_linear_hpo_full_cartesian_{pls,ridge}-tabpfn-hpo-*_seed{0,1,2}/results.csv` (`best_config_json`) | `table_hpo_recipe.tex` | main §Reference methods; supplement §Missing-dataset audit |
| `transfer_latency.py` | the master CSV + `ridge/all54_headline` (Rd25 site splits, `fit_time_s`/`predict_time_s`) | `table_transfer.tex`, `table_latency.tex` | main §Transfer to held-out sites and deployment cost |
| `hpo_union_coverage.py` | the three tuned-linear protocols + `cohort_manifest.csv` | `table_hpo_coverage.tex` | main §Splits/selection/statistics; supplement §Missing-dataset audit |
| `seed_stability.py` | seeds012 (PLS/Ridge/DA/cls) + tuned-HPO seed{0,1,2} CSVs | `table_seed_determinism.tex` | main §Splits/selection; supplement §Seed and split sensitivity |

## Data sources (on disk)

- **Canonical paper runs:** `../../benchmarks/runs/` — `scenarios/paper_aom_aompls_seeds012`,
  `ridge/all54_headline`, `ridge/paper_aom_aomridge_seeds012`, `ridge/paper_aom_aomridge_cls_seeds012`,
  `pls/paper_aom_aompls_da_seeds012`, `scenarios/paper_aom_linear_hpo_full_cartesian_*`.
- **Frozen master:** `../../_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv`
  (83 columns with precomputed `relative_rmsep_vs_*`, `fit_time_s`, `predict_time_s`, `seed`,
  `preprocessing_pipeline`, `source_family`, `domain_group`).
  `\rc{}` **provenance to confirm:** this on-disk build has ~35,930 rows; `nirs4all-lab/.../MASTER_CSV_HASH.txt`
  freezes an earlier 24,879-row snapshot — pin the canonical file/hash before the camera-ready.
- **Cohort map:** `../review/cohort_manifest.csv` (`dataset → source_family / domain_group / split_type`).

## Output path

Each script writes its fragment to the manuscript `tables/` directory. That path is set at the top of
every script (`OUT_*` / `MANU_TABLES`); change it if the manuscript tree moves. The manuscript build
(`build.sh` in the manuscript dir) `\input`s these fragments inside its own table floats.

> The headline regression/runtime/classification tables (`table_main_results`, `table_time_budget`,
> `table_classification_main`, …) come from `../review/build_paper_figures.py`; this `repro/` directory
> adds the five *robustness/coverage/deployment* aggregations (B2/A4/B1/A2/A1) introduced for Talanta.
