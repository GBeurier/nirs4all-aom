#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build small, reproducible browser snapshots from public measured NIR data."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PublicDataset:
    output_id: str
    source_id: str
    target: str
    target_name: str
    wavelength_min: float
    wavelength_max: float
    wavelength_stride: int
    mode: str


DATASETS = (
    PublicDataset(
        "cartilage_thickness",
        "cartilage_spectroscopy_scientificdata_nir",
        "cartilage_thickness",
        "Cartilage thickness (mm)",
        700.0,
        1050.0,
        4,
        "cartilage",
    ),
    PublicDataset(
        "leaf_litter_nitrogen",
        "ecosis_intact_and_ground_leaf_litter_spectra_from_cedar_creek_reflectance_nirs",
        "Nmass",
        "Leaf-litter nitrogen (% dry mass)",
        1000.0,
        2400.0,
        8,
        "independent",
    ),
    PublicDataset(
        "leaf_water_potential",
        "ecosis_tabletop_leaf_drydowns_to_relate_leaf_spectra_and_leaf_reflectance_nirs",
        "lwp_MPa",
        "Leaf water potential (MPa)",
        1000.0,
        2400.0,
        8,
        "grouped_drydown",
    ),
)


def stable_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_table(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream, delimiter=";"))
    if len(rows) < 2:
        raise ValueError(f"Empty source table: {path}")
    return rows[0], rows[1:]


def keyed_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return {row["observation_id"]: row for row in csv.DictReader(stream, delimiter=";")}


def read_source(root: Path, spec: PublicDataset):
    source = root / "datasets" / spec.source_id / "raw"
    x_header, x_rows = read_table(source / "X.csv")
    axis = np.asarray([float(value) for value in x_header[1:]], dtype=np.float64)
    selected = np.flatnonzero((axis >= spec.wavelength_min) & (axis <= spec.wavelength_max))[:: spec.wavelength_stride]
    if len(selected) < 7:
        raise ValueError(f"Too few selected wavelengths for {spec.source_id}")
    spectra = {
        row[0]: np.asarray([float(row[index + 1]) for index in selected], dtype=np.float64)
        for row in x_rows
    }
    return axis[selected], spectra, keyed_rows(source / "Y.csv"), keyed_rows(source / "M.csv")


def finite_target(row: dict[str, str], name: str) -> float | None:
    try:
        value = float(row[name])
    except (KeyError, TypeError, ValueError):
        return None
    if not np.isfinite(value) or value <= -9000:
        return None
    return value


def take_hash_subset(records, limit: int):
    return sorted(records, key=lambda item: stable_key(item[0]))[:limit]


def cartilage_records(spec, spectra, targets, metadata):
    groups: dict[str, list[str]] = defaultdict(list)
    for observation_id in spectra:
        groups[metadata[observation_id]["sample_id"]].append(observation_id)
    records = []
    for sample_id, observation_ids in groups.items():
        target = finite_target(targets[observation_ids[0]], spec.target)
        if target is None:
            continue
        averaged = np.mean([spectra[observation_id] for observation_id in observation_ids], axis=0)
        records.append((sample_id, averaged, target))
    return take_hash_subset(records, 120)


def independent_records(spec, spectra, targets, _metadata):
    records = []
    for observation_id, spectrum in spectra.items():
        target = finite_target(targets[observation_id], spec.target)
        if target is not None:
            records.append((observation_id, spectrum, target))
    return take_hash_subset(records, 120)


def drydown_records(spec, spectra, targets, metadata):
    groups: dict[str, list[tuple[str, np.ndarray, float]]] = defaultdict(list)
    for observation_id, spectrum in spectra.items():
        target = finite_target(targets[observation_id], spec.target)
        if target is not None:
            groups[metadata[observation_id]["sample_id"]].append((observation_id, spectrum, target))
    records = []
    for sample_id, observations in groups.items():
        ordered = sorted(observations, key=lambda item: (item[2], item[0]))
        selected_indices = sorted({0, len(ordered) // 2, len(ordered) - 1})
        records.extend((f"{sample_id}:{ordered[index][0]}", ordered[index][1], ordered[index][2]) for index in selected_indices)
    return records


def split_records(records, mode: str):
    if mode == "grouped_drydown":
        groups: dict[str, list] = defaultdict(list)
        for record in records:
            groups[record[0].split(":", 1)[0]].append(record)
        validation_groups = set(sorted(groups, key=stable_key)[::4])
        calibration = [record for group, values in groups.items() if group not in validation_groups for record in values]
        validation = [record for group, values in groups.items() if group in validation_groups for record in values]
        return calibration, validation
    ordered = sorted(records, key=lambda item: (item[2], stable_key(item[0])))
    validation = [record for index, record in enumerate(ordered) if index % 4 == 3]
    calibration = [record for index, record in enumerate(ordered) if index % 4 != 3]
    return calibration, validation


def write_matrix(path: Path, records, axis: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(f"{value:g}" for value in axis)
        writer.writerows([f"{value:.8f}" for value in record[1]] for record in records)


def write_target(path: Path, records, name: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([name])
        writer.writerows([[f"{record[2]:.8f}"] for record in records])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets-dir", type=Path, required=True, help="Checkout of nirs4all-datasets.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "datasets")
    args = parser.parse_args()

    builders = {
        "cartilage": cartilage_records,
        "independent": independent_records,
        "grouped_drydown": drydown_records,
    }
    for spec in DATASETS:
        axis, spectra, targets, metadata = read_source(args.datasets_dir.resolve(), spec)
        records = builders[spec.mode](spec, spectra, targets, metadata)
        calibration, validation = split_records(records, spec.mode)
        dataset_dir = args.output_dir / spec.output_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        write_matrix(dataset_dir / "Xcal.csv", calibration, axis)
        write_target(dataset_dir / "Ycal.csv", calibration, spec.target_name)
        write_matrix(dataset_dir / "Xval.csv", validation, axis)
        write_target(dataset_dir / "Yval.csv", validation, spec.target_name)
        print(
            f"{spec.output_id}: {len(calibration)} calibration + {len(validation)} validation, "
            f"{len(axis)} measured wavelengths, target {min(record[2] for record in records):.4g}–"
            f"{max(record[2] for record in records):.4g}"
        )


if __name__ == "__main__":
    main()
