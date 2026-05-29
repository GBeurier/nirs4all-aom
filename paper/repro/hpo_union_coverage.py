#!/usr/bin/env python3
"""HPO union coverage (Analysis A2) for the AOM Talanta paper.

Pure aggregation over result CSVs already on disk. NO model fits.

The paper's strict full-HPO denominator is small (PLS-HPO 36, Ridge-HPO 35 of
61 regression datasets -> strict intersection N_cap=32). This script shows the
TRUE tuned-baseline coverage by unioning the three tuned-linear protocols that
already exist on disk, keyed on basename(dataset):

  1. tabpfn-HPO (full preprocessing + model search)
       pls-tabpfn-hpo-25trials  : 36/61
       ridge-tabpfn-hpo-60trials: 35/61
  2. default-cv5 (model hyperparameter only, StandardScaler)
       pls-default-cv5   : 57/61
       ridge-default-cv5 : 58/61
  3. paper-tuned (TabPFN-paper's own tuned PLS/Ridge baselines, in the master CSV
     under source_run == 'tabpfn_paper_master')
       paper-PLS   : 54/61
       paper-Ridge : 54/61

Universe: the 61 regression datasets in cohort_manifest.csv (task == regression).

INPUTS (absolute paths, all already on disk):
  - cohort manifest (universe of 61 regression datasets):
      /home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv
  - default-cv5 results (pls-default-cv5 + ridge-default-cv5):
      .../benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv
  - tabpfn-HPO results (per seed 0/1/2):
      .../paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv
      .../paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv
  - master CSV (paper-tuned rows, source_run == 'tabpfn_paper_master'):
      /home/delete/nirs4all/nirs4all-aom/_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv

OUTPUTS:
  - LaTeX fragment (bare booktabs, no float / caption):
      /home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_hpo_coverage.tex
  - prints all computed numbers to stdout.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

# --- absolute input paths -----------------------------------------------------
COHORT = "/home/delete/nirs4all/nirs4all-aom/paper/review/cohort_manifest.csv"
RUNS = "/home/delete/nirs4all/nirs4all-aom/benchmarks/runs/scenarios"
DEFAULT_CV5 = f"{RUNS}/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv"
PLS_HPO_GLOB = f"{RUNS}/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed*/results.csv"
RIDGE_HPO_GLOB = f"{RUNS}/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed*/results.csv"
MASTER = "/home/delete/nirs4all/nirs4all-aom/_archive/nirs4all-lab_benchmark_master/benchmark_master_results.csv"

# --- absolute output path -----------------------------------------------------
OUT_TABLE = "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_hpo_coverage.tex"


def basename(name: str) -> str:
    """Dataset key used to join across CSVs: drop any leading ``GROUP/`` prefix."""
    return str(name).split("/")[-1]


def ok_datasets(df: pd.DataFrame, variant: str) -> set[str]:
    """Set of basename datasets with a successful (status == 'ok') row for ``variant``."""
    sub = df[(df["variant"] == variant) & (df["status"] == "ok")]
    return set(sub["dataset"].map(basename))


def latex_escape(name: str) -> str:
    """Escape underscores and insert break hints, matching the dir's fragment style."""
    return name.replace("_", "\\_\\allowbreak{}")


def main() -> None:
    # 1. Universe: 61 regression datasets.
    man = pd.read_csv(COHORT)
    reg = man[man["task"] == "regression"]
    universe = set(reg["dataset"])
    n_universe = len(universe)
    assert n_universe == 61, f"expected 61 regression datasets, got {n_universe}"

    # 2. default-cv5 protocol.
    dcv5 = pd.read_csv(DEFAULT_CV5)
    pls_default = ok_datasets(dcv5, "pls-default-cv5") & universe
    ridge_default = ok_datasets(dcv5, "ridge-default-cv5") & universe

    # 3. tabpfn-HPO protocol (pooled over seeds 0/1/2; a dataset counts if it
    #    has >=1 ok row in any seed).
    pls_hpo_df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(PLS_HPO_GLOB))], ignore_index=True)
    ridge_hpo_df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(RIDGE_HPO_GLOB))], ignore_index=True)
    pls_hpo = ok_datasets(pls_hpo_df, "pls-tabpfn-hpo-25trials") & universe
    ridge_hpo = ok_datasets(ridge_hpo_df, "ridge-tabpfn-hpo-60trials") & universe

    # 4. paper-tuned protocol (master CSV, source_run == tabpfn_paper_master).
    master = pd.read_csv(MASTER, usecols=["variant", "dataset", "source_run"], low_memory=False)
    paper = master[master["source_run"] == "tabpfn_paper_master"].copy()
    paper["base"] = paper["dataset"].map(basename)
    pls_paper = set(paper.loc[paper["variant"] == "paper-PLS", "base"]) & universe
    ridge_paper = set(paper.loc[paper["variant"] == "paper-Ridge", "base"]) & universe

    # 5. Union any-tuned coverage + intersection.
    pls_any = pls_hpo | pls_default | pls_paper
    ridge_any = ridge_hpo | ridge_default | ridge_paper
    inter_any = pls_any & ridge_any

    missing_pls = universe - pls_any
    missing_ridge = universe - ridge_any
    missing_inter = universe - inter_any

    # 6. Consistent-protocol intersections (for context).
    inter_hpo = pls_hpo & ridge_hpo
    inter_default = pls_default & ridge_default
    inter_paper = pls_paper & ridge_paper

    # --- report -------------------------------------------------------------
    print(f"Universe (regression datasets): N = {n_universe}")
    print()
    print("Per-protocol coverage (distinct datasets with an ok result):")
    print(f"  PLS-HPO   (pls-tabpfn-hpo-25trials)   : {len(pls_hpo)}/{n_universe}")
    print(f"  Ridge-HPO (ridge-tabpfn-hpo-60trials) : {len(ridge_hpo)}/{n_universe}")
    print(f"  PLS-default-cv5                        : {len(pls_default)}/{n_universe}")
    print(f"  Ridge-default-cv5                      : {len(ridge_default)}/{n_universe}")
    print(f"  paper-PLS                              : {len(pls_paper)}/{n_universe}")
    print(f"  paper-Ridge                            : {len(ridge_paper)}/{n_universe}")
    print()
    print("Consistent-protocol intersections (PLS-and-Ridge both tuned):")
    print(f"  full-HPO    N_cap = {len(inter_hpo)}")
    print(f"  default-cv5 N_cap = {len(inter_default)}")
    print(f"  paper-tuned N_cap = {len(inter_paper)}")
    print()
    print("UNION any-tuned coverage:")
    print(f"  PLS-any-tuned   = {len(pls_any)}/{n_universe}")
    print(f"  Ridge-any-tuned = {len(ridge_any)}/{n_universe}")
    print(f"  N-intersection (any-tuned) = {len(inter_any)}")
    print()
    print(f"Missing PLS-any-tuned   ({len(missing_pls)}): {sorted(missing_pls)}")
    print(f"Missing Ridge-any-tuned ({len(missing_ridge)}): {sorted(missing_ridge)}")
    print(f"Missing intersection    ({len(missing_inter)}): {sorted(missing_inter)}")
    print()

    # Which protocol covers each dataset that the strict full-HPO misses.
    pls_only_paper = sorted((pls_paper - pls_hpo - pls_default))
    pls_only_default = sorted((pls_default - pls_hpo - pls_paper))
    ridge_only_paper = sorted((ridge_paper - ridge_hpo - ridge_default))
    ridge_only_default = sorted((ridge_default - ridge_hpo - ridge_paper))
    print("Datasets the strict full-HPO misses but another protocol rescues:")
    print(f"  PLS covered ONLY by paper-PLS    : {pls_only_paper}")
    print(f"  PLS covered ONLY by default-cv5  : {pls_only_default}")
    print(f"  Ridge covered ONLY by paper-Ridge: {ridge_only_paper}")
    print(f"  Ridge covered ONLY by default-cv5: {ridge_only_default}")

    # --- LaTeX fragment -----------------------------------------------------
    # Bare booktabs fragment (no float, no caption), matching the style of the
    # sibling table_missingness_audit.tex / table_failure_modes.tex fragments.
    # The missing-dataset note is rendered as in-tabular multicolumn rows rather
    # than a \footnote, because the manuscript wraps each fragment in its own
    # floating table where \footnotetext does not render.
    miss_basenames = sorted(missing_inter)
    miss_label = ", ".join(latex_escape(d) for d in miss_basenames)

    lines = []
    lines.append(r"\begin{tabularx}{\linewidth}{Xrr}")
    lines.append(r"\toprule")
    lines.append(r"Tuned-linear protocol & PLS datasets & Ridge datasets \\")
    lines.append(r"\midrule")
    lines.append(rf"\multicolumn{{3}}{{@{{}}l}}{{\emph{{Per-protocol coverage (of {n_universe} regression datasets)}}}} \\")
    lines.append(rf"\quad PLS/Ridge-HPO (full preprocessing search) & {len(pls_hpo)} & {len(ridge_hpo)} \\")
    lines.append(rf"\quad PLS/Ridge-default (model hyperparameter, cv5) & {len(pls_default)} & {len(ridge_default)} \\")
    lines.append(rf"\quad paper-PLS/paper-Ridge (literature-tuned) & {len(pls_paper)} & {len(ridge_paper)} \\")
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{3}{@{}l}{\emph{Union over the three tuned protocols (any-tuned)}} \\")
    lines.append(rf"\quad Any-tuned coverage & {len(pls_any)} & {len(ridge_any)} \\")
    lines.append(rf"\quad $N_{{\cap}}$ (both PLS and Ridge tuned) & {len(inter_any)} & {len(inter_any)} \\")
    lines.append(r"\bottomrule")
    lines.append(
        rf"\multicolumn{{3}}{{@{{}}p{{\linewidth}}}}{{\footnotesize "
        rf"The strict single-protocol full-HPO intersection is "
        rf"$N_{{\cap}}={len(inter_hpo)}$; unioning the three tuned protocols already on "
        rf"disk raises it to $N_{{\cap}}={len(inter_any)}$. The {len(missing_inter)} "
        rf"datasets with no tuned PLS or Ridge result under any protocol are "
        rf"{miss_label}\,---\,both FUSARIUM targets that fail every linear protocol "
        rf"with \code{{ValueError: Input X contains NaN}}.}} \\")
    lines.append(r"\end{tabularx}")
    fragment = "\n".join(lines) + "\n"

    Path(OUT_TABLE).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_TABLE).write_text(fragment)
    print()
    print(f"Wrote LaTeX fragment -> {OUT_TABLE}")


if __name__ == "__main__":
    main()
