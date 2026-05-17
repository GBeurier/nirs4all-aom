"""Shared data helpers for the AOM paper review artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "paper_aom" / "review"
COHORT_MANIFEST = REVIEW / "cohort_manifest.csv"


@dataclass(frozen=True)
class VariantSpec:
    key: str
    workspace: str
    variant_column: str
    variant_value: str
    dataset_column: str = "dataset"
    seed_column: str = "seed"
    status_column: str = "status"
    error_columns: tuple[str, ...] = ("error_message", "error", "status_details")
    require_seeds: int | None = None
    glob: bool = False


LINEAR_DEFAULT = "bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv"
AOMPLS_SEEDS012 = "bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv"
AOMRIDGE_HEADLINE = "bench/AOM_v0/Ridge/benchmark_runs/all54_headline/results.csv"

PAPER_VARIANT_SPECS: tuple[VariantSpec, ...] = (
    VariantSpec(
        key="pls-default-cv5",
        workspace=LINEAR_DEFAULT,
        variant_column="variant",
        variant_value="pls-default-cv5",
    ),
    VariantSpec(
        key="ridge-default-cv5",
        workspace=LINEAR_DEFAULT,
        variant_column="variant",
        variant_value="ridge-default-cv5",
    ),
    VariantSpec(
        key="pls-tabpfn-hpo-25trials",
        workspace="bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed*/results.csv",
        variant_column="variant",
        variant_value="pls-tabpfn-hpo-25trials",
        require_seeds=3,
        glob=True,
    ),
    VariantSpec(
        key="ridge-tabpfn-hpo-60trials",
        workspace="bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed*/results.csv",
        variant_column="variant",
        variant_value="ridge-tabpfn-hpo-60trials",
        require_seeds=3,
        glob=True,
    ),
    VariantSpec(
        key="ASLS-AOM-compact-cv5-numpy",
        workspace=AOMPLS_SEEDS012,
        variant_column="result_label",
        variant_value="ASLS-AOM-compact-cv5-numpy",
        require_seeds=3,
    ),
    VariantSpec(
        key="AOM-compact-cv5-numpy",
        workspace=AOMPLS_SEEDS012,
        variant_column="result_label",
        variant_value="AOM-compact-cv5-numpy",
        require_seeds=3,
    ),
    VariantSpec(
        key="AOMRidge-global-compact-none",
        workspace=AOMRIDGE_HEADLINE,
        variant_column="variant",
        variant_value="AOMRidge-global-compact-none",
        seed_column="random_state",
        error_columns=("error", "error_message", "status_details"),
    ),
    VariantSpec(
        key="AOMRidge-Blender-headline-spxy3",
        workspace=AOMRIDGE_HEADLINE,
        variant_column="variant",
        variant_value="AOMRidge-Blender-headline-spxy3",
        seed_column="random_state",
        error_columns=("error", "error_message", "status_details"),
    ),
)


def dataset_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.split("/").str[-1].str.strip()


def ok_status(series: pd.Series) -> pd.Series:
    return series.astype("string").str.lower().fillna("").isin({"ok", "success", "completed", ""})


def _clean_message(text: object, limit: int = 120) -> str:
    msg = " ".join(str(text or "").split())
    return msg[:limit]


def reference_regression_datasets() -> list[str]:
    manifest = pd.read_csv(COHORT_MANIFEST)
    if "task" in manifest.columns:
        manifest = manifest[manifest["task"].astype("string").str.lower() == "regression"]
    return sorted(dataset_id(manifest["dataset"]).dropna().unique().tolist())


def _paths_for_spec(spec: VariantSpec) -> list[Path]:
    if spec.glob:
        return sorted(ROOT.glob(spec.workspace))
    path = ROOT / spec.workspace
    return [path] if path.exists() else []


def _read_spec_rows(spec: VariantSpec) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in _paths_for_spec(spec):
        raw = pd.read_csv(path, low_memory=False)
        if spec.variant_column not in raw.columns or spec.dataset_column not in raw.columns:
            continue
        sub = raw[
            raw[spec.variant_column].astype("string").str.lower()
            == spec.variant_value.lower()
        ].copy()
        if sub.empty:
            continue
        sub["dataset"] = dataset_id(sub[spec.dataset_column])
        if spec.status_column in sub.columns:
            sub["_status"] = sub[spec.status_column].astype("string").str.lower().fillna("")
        else:
            sub["_status"] = ""
        if spec.seed_column in sub.columns:
            sub["_seed"] = pd.to_numeric(sub[spec.seed_column], errors="coerce")
        else:
            sub["_seed"] = 0
        messages = []
        for _, row in sub.iterrows():
            msg = ""
            for col in spec.error_columns:
                if col in sub.columns and pd.notna(row.get(col)) and str(row.get(col)).strip():
                    msg = _clean_message(row.get(col), limit=1000)
                    break
            messages.append(msg)
        sub["_error_message"] = messages
        sub["_source_file"] = str(path.relative_to(ROOT))
        frames.append(sub[["dataset", "_seed", "_status", "_error_message", "_source_file"]])
    if not frames:
        return pd.DataFrame(columns=["dataset", "_seed", "_status", "_error_message", "_source_file"])
    return pd.concat(frames, ignore_index=True)


def variant_status_table(reference: list[str] | None = None) -> dict[str, pd.DataFrame]:
    reference = reference_regression_datasets() if reference is None else sorted(reference)
    reference_set = set(reference)
    out: dict[str, pd.DataFrame] = {}
    for spec in PAPER_VARIANT_SPECS:
        rows = _read_spec_rows(spec)
        records = []
        for dataset in reference:
            ds_rows = rows[rows["dataset"] == dataset]
            if ds_rows.empty:
                status = "not attempted"
                ok_seeds = 0
                error_message = ""
            else:
                ok_rows = ds_rows[ok_status(ds_rows["_status"])]
                ok_seed_values = ok_rows["_seed"].dropna().unique()
                ok_seeds = int(len(ok_seed_values)) if spec.require_seeds else int(not ok_rows.empty)
                has_error = bool((~ok_status(ds_rows["_status"])).any())
                if spec.require_seeds:
                    if ok_seeds >= spec.require_seeds:
                        status = "ok"
                    elif has_error:
                        status = "error"
                    else:
                        status = f"ok seeds<{spec.require_seeds}"
                else:
                    status = "ok" if ok_seeds else ("error" if has_error else "not attempted")
                error_values = [str(v).strip() for v in ds_rows["_error_message"].dropna() if str(v).strip()]
                error_message = _clean_message("; ".join(error_values), limit=120)
            records.append(
                {
                    "dataset": dataset,
                    "status": status,
                    "ok_seeds": ok_seeds,
                    "error_message": error_message[:120],
                }
            )
        table = pd.DataFrame(records)
        # Keep any extra successful datasets visible to callers computing
        # intersections, but the working artifact is reference-cohort based.
        extra = sorted(set(rows["dataset"].dropna().unique()) - reference_set)
        if extra:
            extras = []
            for dataset in extra:
                ds_rows = rows[rows["dataset"] == dataset]
                ok_rows = ds_rows[ok_status(ds_rows["_status"])]
                ok_seeds = int(len(ok_rows["_seed"].dropna().unique())) if spec.require_seeds else int(not ok_rows.empty)
                status = "ok" if (ok_seeds >= (spec.require_seeds or 1)) else "error"
                extras.append({"dataset": dataset, "status": status, "ok_seeds": ok_seeds, "error_message": ""})
            table = pd.concat([table, pd.DataFrame(extras)], ignore_index=True)
        out[spec.key] = table
    return out


def ok_datasets_by_variant(reference: list[str] | None = None) -> dict[str, set[str]]:
    statuses = variant_status_table(reference)
    return {
        key: set(table.loc[table["status"] == "ok", "dataset"].astype(str))
        for key, table in statuses.items()
    }


def strict_intersection() -> list[str]:
    ok_sets = ok_datasets_by_variant()
    if not ok_sets:
        return []
    keep = set.intersection(*ok_sets.values())
    return sorted(keep)


def filter_to_datasets(df: pd.DataFrame, datasets: set[str] | list[str]) -> pd.DataFrame:
    if df.empty or "dataset" not in df.columns:
        return df.copy()
    keep = set(datasets)
    out = df.copy()
    out["dataset"] = dataset_id(out["dataset"])
    return out[out["dataset"].isin(keep)].copy()


def write_missing_datasets_doc(output_path: Path | None = None) -> Path:
    output_path = output_path or (REVIEW / "missing_datasets_per_variant.md")
    reference = reference_regression_datasets()
    reference_set = set(reference)
    keep = strict_intersection()
    status_tables = variant_status_table(reference)

    lines: list[str] = [
        "# Missing datasets per paper variant",
        "",
        "Generated by Codex v7 on 2026-05-17 from the current workspace CSVs.  "
        "This file is a working artifact for filling the gaps; it is not referenced from the paper.",
        "",
        "## Reference cohort",
        "",
        f"Source: `paper_aom/review/cohort_manifest.csv` -- N attempted = {len(reference)}.",
        "",
        "## Strict intersection used in the paper",
        "",
        f"N_∩ = {len(keep)} datasets.  Full list:",
        "",
    ]
    lines.extend(f"- {dataset}" for dataset in keep)
    lines += [
        "",
        "## Per-variant status",
        "",
        "| Variant key | Workspace path | OK seeds=3 | OK seeds<3 | error | not attempted |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    spec_by_key = {spec.key: spec for spec in PAPER_VARIANT_SPECS}
    for spec in PAPER_VARIANT_SPECS:
        table = status_tables[spec.key]
        ref_table = table[table["dataset"].isin(reference_set)]
        ok_count = int((ref_table["status"] == "ok").sum())
        less_count = int(ref_table["status"].astype(str).str.contains("ok seeds<", regex=False).sum())
        error_count = int((ref_table["status"] == "error").sum())
        absent_count = int((ref_table["status"] == "not attempted").sum())
        less_text = str(less_count) if spec.require_seeds else "--"
        lines.append(
            f"| {spec.key} | `{spec.workspace}` | {ok_count} | {less_text} | {error_count} | {absent_count} |"
        )

    lines += ["", "## Missing rows per variant (vs reference cohort)", ""]
    for key, table in status_tables.items():
        spec = spec_by_key[key]
        ref_table = table[table["dataset"].isin(reference_set)].copy()
        missing = ref_table[ref_table["status"] != "ok"].sort_values("dataset")
        lines.append(f"### {key} -- missing {len(missing)}")
        lines.append("")
        lines.append("| Dataset | status | error message (truncated to 120 chars) |")
        lines.append("| --- | --- | --- |")
        if missing.empty:
            lines.append("| -- | -- | -- |")
        else:
            for _, row in missing.iterrows():
                msg = str(row.get("error_message", "") or "")
                lines.append(f"| {row['dataset']} | {row['status']} | {msg} |")
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n")
    return output_path
