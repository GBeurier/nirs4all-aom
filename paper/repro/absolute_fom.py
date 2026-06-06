#!/usr/bin/env python3
"""Absolute figures-of-merit table for the AOM Talanta paper.

Pure aggregation over result CSVs already on disk. No model is fit here.

The consistency gate intentionally reproduces the paper's already-published
paired RMSEP ratios before the LaTeX fragment is written. If those checks fail,
the script exits without emitting the table.
"""

from __future__ import annotations

import csv
import io
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


AOM_ROOT = Path("/home/delete/nirs4all/nirs4all-aom")
RUNS = AOM_ROOT / "benchmarks" / "runs"
SCEN = RUNS / "scenarios"

COHORT = AOM_ROOT / "paper" / "review" / "cohort_manifest.csv"
PATH_AOMPLS = SCEN / "paper_aom_aompls_seeds012" / "results.csv"
PATH_AOMRIDGE_HEADLINE = RUNS / "ridge" / "all54_headline" / "results.csv"
PATH_DEFAULT = SCEN / "paper_aom_linear_hpo_full_cartesian_default_cv5_all" / "results.csv"
PATH_PLS_HPO = tuple(
    SCEN / f"paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{s}" / "results.csv"
    for s in (0, 1, 2)
)
PATH_RIDGE_HPO = tuple(
    SCEN / f"paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{s}" / "results.csv"
    for s in (0, 1, 2)
)

OUT_TABLE = Path(
    "/home/delete/nirs4all/nirs4all-papers/aom_talanta_26/manuscript/tables/"
    "table_absolute_fom.tex"
)

EXPECTED_RIDGE_SIMPLE_VS_DEFAULT = 0.974
EXPECTED_PLS_SIMPLE_VS_DEFAULT = 0.991
CONSISTENCY_TOL = 0.005


@dataclass(frozen=True)
class VariantSpec:
    """CSV locator for one paper variant.

    This mirrors the variant specs used by paper/review/paper_data.py, but keeps
    this aggregation stdlib-only so it can run without pandas.
    """

    key: str
    paths: tuple[Path, ...]
    variant_column: str
    variant_value: str
    rmsep_column: str
    r2_column: str | None = None
    dataset_column: str = "dataset"
    seed_column: str = "seed"
    status_column: str = "status"
    require_seeds: int | None = None


PLS_DEFAULT = VariantSpec(
    key="pls-default-cv5",
    paths=(PATH_DEFAULT,),
    variant_column="variant",
    variant_value="pls-default-cv5",
    rmsep_column="rmsep",
    r2_column="r2",
)
RIDGE_DEFAULT = VariantSpec(
    key="ridge-default-cv5",
    paths=(PATH_DEFAULT,),
    variant_column="variant",
    variant_value="ridge-default-cv5",
    rmsep_column="rmsep",
    r2_column="r2",
)
PLS_HPO = VariantSpec(
    key="pls-hpo",
    paths=PATH_PLS_HPO,
    variant_column="variant",
    variant_value="pls-tabpfn-hpo-25trials",
    rmsep_column="rmsep",
    r2_column="r2",
    require_seeds=3,
)
RIDGE_HPO = VariantSpec(
    key="ridge-hpo",
    paths=PATH_RIDGE_HPO,
    variant_column="variant",
    variant_value="ridge-tabpfn-hpo-60trials",
    rmsep_column="rmsep",
    r2_column="r2",
    require_seeds=3,
)
AOMPLS_BEST = VariantSpec(
    key="ASLS-AOM-compact-cv5-numpy",
    paths=(PATH_AOMPLS,),
    variant_column="result_label",
    variant_value="ASLS-AOM-compact-cv5-numpy",
    rmsep_column="RMSEP",
    r2_column="r2_test",
    require_seeds=3,
)
AOMPLS_SIMPLE = VariantSpec(
    key="AOM-compact-cv5-numpy",
    paths=(PATH_AOMPLS,),
    variant_column="result_label",
    variant_value="AOM-compact-cv5-numpy",
    rmsep_column="RMSEP",
    r2_column="r2_test",
    require_seeds=3,
)
AOMRIDGE_SIMPLE = VariantSpec(
    key="AOMRidge-global-compact-none",
    paths=(PATH_AOMRIDGE_HEADLINE,),
    variant_column="variant",
    variant_value="AOMRidge-global-compact-none",
    rmsep_column="rmsep",
    r2_column="r2",
    seed_column="random_state",
)
AOMRIDGE_BEST = VariantSpec(
    key="AOMRidge-Blender-headline-spxy3",
    paths=(PATH_AOMRIDGE_HEADLINE,),
    variant_column="variant",
    variant_value="AOMRidge-Blender-headline-spxy3",
    rmsep_column="rmsep",
    r2_column="r2",
    seed_column="random_state",
)

STRICT_SPECS = (
    PLS_DEFAULT,
    RIDGE_DEFAULT,
    PLS_HPO,
    RIDGE_HPO,
    AOMPLS_BEST,
    AOMPLS_SIMPLE,
    AOMRIDGE_SIMPLE,
    AOMRIDGE_BEST,
)

TABLE_SPECS = (AOMPLS_SIMPLE, PLS_HPO, AOMRIDGE_SIMPLE, RIDGE_HPO)
N_TEST_SPECS = (PLS_DEFAULT, RIDGE_DEFAULT, PLS_HPO, RIDGE_HPO)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    # all54_headline contains embedded NUL bytes in the committed CSV; sanitize
    # before DictReader so the stdlib fallback remains usable.
    text = path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
    return list(csv.DictReader(io.StringIO(text)))


def dataset_id(value: object) -> str:
    return str(value).split("/")[-1].strip()


def ok_status(value: object) -> bool:
    return str(value or "").strip().lower() in {"", "ok", "success", "completed"}


def parse_float(value: object) -> float | None:
    try:
        out = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def matching_rows(spec: VariantSpec) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    target = spec.variant_value.lower()
    for path in spec.paths:
        for row in read_csv_rows(path):
            if row.get(spec.variant_column, "").strip().lower() != target:
                continue
            if spec.status_column in row and not ok_status(row.get(spec.status_column)):
                continue
            if not row.get(spec.dataset_column):
                continue
            rows.append(row)
    return rows


def reference_regression_datasets() -> list[str]:
    rows = read_csv_rows(COHORT)
    out = [
        dataset_id(row["dataset"])
        for row in rows
        if row.get("task", "").strip().lower() == "regression" and row.get("dataset")
    ]
    return sorted(set(out))


def ok_datasets(spec: VariantSpec, reference: set[str]) -> set[str]:
    seeds_by_dataset: dict[str, set[str]] = defaultdict(set)
    for row in matching_rows(spec):
        ds = dataset_id(row[spec.dataset_column])
        if ds not in reference:
            continue
        seed = row.get(spec.seed_column, "__single__")
        seeds_by_dataset[ds].add(str(seed))
    if spec.require_seeds is None:
        return set(seeds_by_dataset)
    return {ds for ds, seeds in seeds_by_dataset.items() if len(seeds) >= spec.require_seeds}


def strict_intersection() -> tuple[list[str], dict[str, int]]:
    reference = set(reference_regression_datasets())
    per_variant = {spec.key: ok_datasets(spec, reference) for spec in STRICT_SPECS}
    keep = set.intersection(*per_variant.values())
    counts = {key: len(value) for key, value in per_variant.items()}
    return sorted(keep), counts


def per_dataset_metric(spec: VariantSpec, column: str, datasets: set[str]) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for row in matching_rows(spec):
        ds = dataset_id(row[spec.dataset_column])
        if ds not in datasets:
            continue
        value = parse_float(row.get(column))
        if value is None:
            continue
        values[ds].append(value)
    return {ds: statistics.fmean(vals) for ds, vals in values.items() if vals}


def collect_n_test(datasets: set[str]) -> dict[str, int]:
    values: dict[str, set[int]] = defaultdict(set)
    for spec in N_TEST_SPECS:
        for row in matching_rows(spec):
            ds = dataset_id(row[spec.dataset_column])
            if ds not in datasets:
                continue
            value = parse_float(row.get("n_test"))
            if value is not None:
                values[ds].add(int(round(value)))
    conflicts = {ds: sorted(v) for ds, v in values.items() if len(v) > 1}
    if conflicts:
        lines = [f"{ds}: {vals}" for ds, vals in sorted(conflicts.items())]
        raise RuntimeError("conflicting n_test values across result CSVs:\n" + "\n".join(lines))
    missing = sorted(datasets - set(values))
    if missing:
        raise RuntimeError("missing n_test in result CSVs for: " + ", ".join(missing))
    return {ds: next(iter(vals)) for ds, vals in values.items()}


def median_ratio(candidate: dict[str, float], reference: dict[str, float], datasets: list[str]) -> tuple[float, list[dict[str, float | str]]]:
    rows: list[dict[str, float | str]] = []
    for ds in datasets:
        cand = candidate.get(ds)
        ref = reference.get(ds)
        if cand is None or ref is None or ref <= 0:
            continue
        rows.append({"dataset": ds, "candidate": cand, "reference": ref, "ratio": cand / ref})
    if not rows:
        raise RuntimeError("no paired rows available for median ratio")
    return statistics.median(float(row["ratio"]) for row in rows), rows


def latex_escape(value: object) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "/": r"/\allowbreak{}",
        "-": r"-\allowbreak{}",
    }
    return "".join(repl.get(ch, ch) for ch in str(value))


def fmt_rmsep(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    av = abs(value)
    if av == 0:
        return "0"
    if av < 0.01:
        return f"{value:.4g}"
    if av < 1:
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if av < 10:
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if av < 100:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if av < 1000:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.0f}"


def fmt_r2(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    return f"{value:.3f}"


def rpd_from_r2(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    if value < 0 or value >= 1:
        return None
    value = min(value, 1.0 - 1e-12)
    return 1.0 / math.sqrt(1.0 - value)


def fmt_rpd(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    return f"{value:.2f}"


def consistency_check(datasets: list[str]) -> tuple[bool, list[str]]:
    dataset_set = set(datasets)
    aomridge = per_dataset_metric(AOMRIDGE_SIMPLE, AOMRIDGE_SIMPLE.rmsep_column, dataset_set)
    ridge_default = per_dataset_metric(RIDGE_DEFAULT, RIDGE_DEFAULT.rmsep_column, dataset_set)
    aompls = per_dataset_metric(AOMPLS_SIMPLE, AOMPLS_SIMPLE.rmsep_column, dataset_set)
    pls_default = per_dataset_metric(PLS_DEFAULT, PLS_DEFAULT.rmsep_column, dataset_set)

    checks = [
        (
            "AOM-Ridge (simple) vs Ridge-default",
            EXPECTED_RIDGE_SIMPLE_VS_DEFAULT,
            *median_ratio(aomridge, ridge_default, datasets),
        ),
        (
            "AOM-PLS (simple) vs PLS-default",
            EXPECTED_PLS_SIMPLE_VS_DEFAULT,
            *median_ratio(aompls, pls_default, datasets),
        ),
    ]

    ok = True
    lines = []
    for label, expected, got, rows in checks:
        delta = got - expected
        count_ok = len(rows) == len(datasets)
        within_tol = abs(delta) <= CONSISTENCY_TOL
        passed = count_ok and within_tol
        ok = ok and passed
        lines.append(
            f"{label}: N={len(rows)} median={got:.6f} expected~{expected:.3f} "
            f"delta={delta:+.6f} -> {'PASS' if passed else 'FAIL'}"
        )
        if not passed:
            lines.append("  Paired rows used for the failing comparison:")
            for row in sorted(rows, key=lambda r: str(r["dataset"])):
                lines.append(
                    "  "
                    f"{row['dataset']}: candidate={float(row['candidate']):.8g} "
                    f"reference={float(row['reference']):.8g} ratio={float(row['ratio']):.6f}"
                )
    return ok, lines


def build_table_rows(datasets: list[str]) -> list[dict[str, object]]:
    dataset_set = set(datasets)
    n_test = collect_n_test(dataset_set)
    aompls = per_dataset_metric(AOMPLS_SIMPLE, AOMPLS_SIMPLE.rmsep_column, dataset_set)
    pls_hpo = per_dataset_metric(PLS_HPO, PLS_HPO.rmsep_column, dataset_set)
    aomridge = per_dataset_metric(AOMRIDGE_SIMPLE, AOMRIDGE_SIMPLE.rmsep_column, dataset_set)
    ridge_hpo = per_dataset_metric(RIDGE_HPO, RIDGE_HPO.rmsep_column, dataset_set)
    aomridge_r2 = per_dataset_metric(AOMRIDGE_SIMPLE, AOMRIDGE_SIMPLE.r2_column or "r2", dataset_set)

    missing = []
    rows = []
    for ds in datasets:
        required = {
            "n_test": n_test.get(ds),
            "aompls_rmsep": aompls.get(ds),
            "pls_hpo_rmsep": pls_hpo.get(ds),
            "aomridge_rmsep": aomridge.get(ds),
            "ridge_hpo_rmsep": ridge_hpo.get(ds),
            "aomridge_r2": aomridge_r2.get(ds),
        }
        absent = [key for key, value in required.items() if value is None]
        if absent:
            missing.append(f"{ds}: {', '.join(absent)}")
            continue
        rpd = rpd_from_r2(float(required["aomridge_r2"]))
        rows.append({"dataset": ds, **required, "aomridge_rpd": rpd})
    if missing:
        raise RuntimeError("missing table values after strict-intersection filtering:\n" + "\n".join(missing))
    return rows


def write_latex(rows: list[dict[str, object]]) -> str:
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrrrrr}",
        r"\toprule",
        r"Dataset & $n_{\mathrm{test}}$ & \multicolumn{4}{c}{RMSEP (original units)} & AOM-\allowbreak{}Ridge & AOM-\allowbreak{}Ridge \\",
        r"\cmidrule(lr){3-6}",
        r" & & AOM-\allowbreak{}PLS & PLS-\allowbreak{}HPO & AOM-\allowbreak{}Ridge & Ridge-\allowbreak{}HPO & $R^2$ & RPD \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{latex_escape(row['dataset'])} & {row['n_test']} & "
            f"{fmt_rmsep(float(row['aompls_rmsep']))} & "
            f"{fmt_rmsep(float(row['pls_hpo_rmsep']))} & "
            f"{fmt_rmsep(float(row['aomridge_rmsep']))} & "
            f"{fmt_rmsep(float(row['ridge_hpo_rmsep']))} & "
            f"{fmt_r2(float(row['aomridge_r2']))} & "
            f"{fmt_rpd(row['aomridge_rpd'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    text = "\n".join(lines)
    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    OUT_TABLE.write_text(text)
    return text


def print_rows(rows: list[dict[str, object]]) -> None:
    print()
    print("Per-dataset absolute figures of merit:")
    print("dataset,n_test,AOM-PLS_RMSEP,PLS-HPO_RMSEP,AOM-Ridge_RMSEP,Ridge-HPO_RMSEP,AOM-Ridge_R2,AOM-Ridge_RPD")
    for row in rows:
        print(
            f"{row['dataset']},{row['n_test']},"
            f"{fmt_rmsep(float(row['aompls_rmsep']))},"
            f"{fmt_rmsep(float(row['pls_hpo_rmsep']))},"
            f"{fmt_rmsep(float(row['aomridge_rmsep']))},"
            f"{fmt_rmsep(float(row['ridge_hpo_rmsep']))},"
            f"{fmt_r2(float(row['aomridge_r2']))},"
            f"{fmt_rpd(row['aomridge_rpd'])}"
        )


def main() -> None:
    print("=" * 78)
    print("ABSOLUTE FOM TABLE  (pure aggregation, no fits)")
    print("=" * 78)

    datasets, counts = strict_intersection()
    print(f"Strict headline intersection N_cap = {len(datasets)}")
    print("OK dataset counts by strict-intersection variant:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")

    print()
    print("Consistency check against published paired ratios:")
    passed, lines = consistency_check(datasets)
    for line in lines:
        print(line)
    if not passed:
        print()
        print(f"FAILED: no LaTeX table emitted; tolerance is +/-{CONSISTENCY_TOL:.3f}.")
        raise SystemExit(2)

    print(f"PASSED: both medians are within +/-{CONSISTENCY_TOL:.3f}.")

    rows = build_table_rows(datasets)
    write_latex(rows)
    print_rows(rows)
    print()
    print(f"Wrote LaTeX fragment -> {OUT_TABLE}")


if __name__ == "__main__":
    main()
