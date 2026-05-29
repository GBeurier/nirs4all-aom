#!/usr/bin/env python3
"""ANALYSIS A4 -- de-facto fixed conventional recipe from HPO selections.

Pure aggregation over result CSVs already on disk -- NO model fits.

The strong-conventional preprocessing space searched under TabPFN-guided HPO is
  norm     in {none, snv, msc, emsc2}
  smooth   in {none, Savitzky-Golay sg_<window>_<polyorder>_<deriv>, Gaussian gauss_<deriv>_<sigma>}
  baseline in {none, detrend, asls}
  osc      in {none, osc_1, osc_2, osc_3}
  + model hyperparameter (PLS n_components / Ridge alpha)
This script parses ``best_config_json`` across the 3 seeds (0/1/2) of the two
HPO scenarios, tabulates the SELECTION FREQUENCY of each norm / smooth / baseline
/ osc choice and the top combined (norm | smooth | baseline) recipes, separately
for PLS-HPO (~108 fits) and Ridge-HPO (~105 fits), and reports the
most-frequently-selected ("de-facto fixed") recipe for each. Savitzky-Golay codes
are decoded as sg_<window>_<polyorder>_<deriv>.

INPUTS (absolute paths, read-only):
  benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv
  benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv
    (under /home/delete/nirs4all/nirs4all-aom/)

OUTPUTS:
  stdout: the selection-frequency tables and the de-facto recipe finding
  LaTeX table fragment (bare, booktabs, no float/caption):
    /home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_hpo_recipe.tex

SANITY CHECK reproduced from paper/review/final_stats.md neighbourhood
(_survey/existing_scores_hunt.md A4 section, lines 304-305):
  PLS-HPO  norm none49/snv48/msc8/emsc2_3 ; top combo snv|none|detrend (7)
  Ridge-HPO norm snv64/none31/msc10 ; top combo snv|gauss_0_2|none tie snv|gauss_0_2|detrend (9)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

AOM_ROOT = Path("/home/delete/nirs4all/nirs4all-aom")
SCEN = AOM_ROOT / "benchmarks/runs/scenarios"
TABLE_OUT = Path(
    "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/table_hpo_recipe.tex"
)

SCENARIOS = {
    "PLS-HPO": "paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials",
    "Ridge-HPO": "paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials",
}
SEEDS = (0, 1, 2)
COMPONENTS = ("norm", "smooth", "baseline", "osc")


def load_configs(scenario_stub: str) -> pd.DataFrame:
    """Return one row per successful HPO fit with its selected preprocessing config."""
    records = []
    for seed in SEEDS:
        csv = SCEN / f"{scenario_stub}_seed{seed}" / "results.csv"
        df = pd.read_csv(csv)
        ok = df[df["status"] == "ok"]
        for _, row in ok.iterrows():
            cfg = json.loads(row["best_config_json"])
            records.append(
                {
                    "dataset": row["dataset"],
                    "seed": seed,
                    "norm": cfg["norm"],
                    "smooth": cfg["smooth"],
                    "baseline": cfg["baseline"],
                    "osc": cfg["osc"],
                }
            )
    return pd.DataFrame.from_records(records)


def decode_smooth(code: str) -> str:
    """Decode a smoother code into a human-readable label.

    sg_<window>_<polyorder>_<deriv> -> Savitzky-Golay window W, order P, derivative D
    gauss_<deriv>_<sigma>           -> Gaussian derivative D, sigma S
    none                            -> none
    """
    if code == "none":
        return "none"
    if code.startswith("sg_"):
        _, w, p, d = code.split("_")
        return f"SG w{w} p{p} d{d}"
    if code.startswith("gauss_"):
        _, d, s = code.split("_")
        return f"Gaussian d{d} sigma{s}"
    return code


def frequency_report(df: pd.DataFrame, label: str) -> dict:
    n = len(df)
    out = {"label": label, "n_fits": n, "n_datasets": df["dataset"].nunique()}
    print(f"\n=== {label}  (n_fits={n}, datasets={out['n_datasets']}) ===")
    out["choices"] = {}
    for comp in COMPONENTS:
        c = Counter(df[comp])
        out["choices"][comp] = c.most_common()
        pretty = "  ".join(f"{k}:{v}" for k, v in c.most_common())
        print(f"  {comp:9s}: {pretty}")
    combo = Counter(
        f"{r.norm}|{r.smooth}|{r.baseline}" for r in df.itertuples(index=False)
    )
    out["combos"] = combo.most_common()
    print("  top (norm|smooth|baseline) recipes:")
    for recipe, cnt in combo.most_common(8):
        norm, smooth, baseline = recipe.split("|")
        print(f"     {recipe:32s} {cnt:3d}  [{norm} | {decode_smooth(smooth)} | {baseline}]")
    top_n = combo.most_common(1)[0][1]
    out["top_recipes"] = [r for r in combo.most_common() if r[1] == top_n]
    return out


def _tex(s: str) -> str:
    """Escape underscores and add break hints, matching the existing fragment style."""
    return s.replace("_", r"\_\allowbreak{}")


def fmt_choice_line(report: dict, comp: str, k: int = 3) -> str:
    """'choice (count, pct%)' for the top-k choices of one component."""
    n = report["n_fits"]
    parts = []
    for choice, cnt in report["choices"][comp][:k]:
        label = decode_smooth(choice) if comp == "smooth" else choice
        parts.append(f"{_tex(label)} ({cnt}, {100 * cnt / n:.0f}\\%)")
    return "; ".join(parts)


def fmt_combo_line(report: dict, k: int = 2) -> str:
    n = report["n_fits"]
    parts = []
    for recipe, cnt in report["combos"][:k]:
        norm, smooth, baseline = recipe.split("|")
        nice = f"{norm} $|$ {decode_smooth(smooth)} $|$ {baseline}"
        parts.append(f"{_tex(nice)} ({cnt}, {100 * cnt / n:.0f}\\%)")
    return "; ".join(parts)


def write_table(pls: dict, ridge: dict, path: Path) -> None:
    """Write a bare booktabs tabularx fragment: component | top choices, per model."""
    comp_label = {
        "norm": "Normalisation",
        "smooth": "Smoothing / derivative",
        "baseline": "Baseline",
        "osc": "OSC components",
    }
    lines = [r"\begin{tabularx}{\linewidth}{l X}", r"\toprule"]
    lines.append(
        r"Component & Most-frequently-selected choices (count, share of fits) \\"
    )
    # PLS section
    lines.append(r"\midrule")
    lines.append(
        rf"\multicolumn{{2}}{{l}}{{\emph{{PLS-HPO}} -- {pls['n_fits']} fits over "
        rf"{pls['n_datasets']} datasets (seeds 0/1/2)}} \\"
    )
    for comp in COMPONENTS:
        lines.append(f"{comp_label[comp]} & {fmt_choice_line(pls, comp)} \\\\")
    lines.append(rf"Top recipe (norm $|$ smooth $|$ baseline) & {fmt_combo_line(pls)} \\")
    # Ridge section
    lines.append(r"\midrule")
    lines.append(
        rf"\multicolumn{{2}}{{l}}{{\emph{{Ridge-HPO}} -- {ridge['n_fits']} fits over "
        rf"{ridge['n_datasets']} datasets (seeds 0/1/2)}} \\"
    )
    for comp in COMPONENTS:
        lines.append(f"{comp_label[comp]} & {fmt_choice_line(ridge, comp)} \\\\")
    lines.append(rf"Top recipe (norm $|$ smooth $|$ baseline) & {fmt_combo_line(ridge)} \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabularx}")
    path.write_text("\n".join(lines) + "\n")
    print(f"\nWrote LaTeX fragment -> {path}")


def main() -> None:
    pls_df = load_configs(SCENARIOS["PLS-HPO"])
    ridge_df = load_configs(SCENARIOS["Ridge-HPO"])

    pls = frequency_report(pls_df, "PLS-HPO")
    ridge = frequency_report(ridge_df, "Ridge-HPO")

    print("\n--- De-facto fixed recipe (honest finding) ---")
    for rep in (pls, ridge):
        winners = ", ".join(f"{r} (n={c})" for r, c in rep["top_recipes"])
        n = rep["n_fits"]
        top_cnt = rep["top_recipes"][0][1]
        print(
            f"{rep['label']}: most-frequent (norm|smooth|baseline) = {winners} "
            f"-> {top_cnt}/{n} = {100 * top_cnt / n:.0f}% of fits. "
            "No single recipe dominates; selection is dataset-dependent."
        )

    TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
    write_table(pls, ridge, TABLE_OUT)


if __name__ == "__main__":
    main()
