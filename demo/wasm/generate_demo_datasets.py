#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build compact, deterministic demo subsets from public nirs4all datasets."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Recipe:
    dataset_id: str
    source_id: str
    target_column: str
    target_label: str
    seed: int
    n_calibration: int = 90
    n_validation: int = 30


RECIPES = (
    Recipe(
        "squash_glucose",
        "ecosis_cucurbita_pepo_two_stresses_leaf_canopy_reflectance_nirs",
        "Glucose",
        "Glucose",
        101,
    ),
    Recipe(
        "crop_nitrogen",
        "ecosis_leaf_spectra_structural_and_biochemical_leaf_traits_of_reflectance_nirs",
        "N_pc_dry",
        "Nitrogen (% dry mass)",
        202,
    ),
    Recipe(
        "leaf_water",
        "ecosis_tabletop_leaf_drydowns_to_relate_leaf_spectra_and_leaf_reflectance_nirs",
        "lwp_MPa",
        "Leaf water potential (MPa)",
        303,
    ),
)


def parse_number(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def validate_redistribution(dataset_dir: Path) -> None:
    card_path = dataset_dir / "dataset_card.json"
    if not card_path.is_file():
        raise FileNotFoundError(f"Missing dataset card: {card_path}")
    with card_path.open(encoding="utf-8") as stream:
        card = json.load(stream)
    license_summary = card.get("license_summary", {})
    rights = card.get("rights", {})
    if (
        license_summary.get("redistribution_status") != "cleared"
        or rights.get("public_release_allowed") is not True
    ):
        raise RuntimeError(
            f"Redistribution is not cleared for {dataset_dir.name}; "
            "refusing to build a public demo subset."
        )


def select_wavelengths(header: list[str], maximum: int = 301) -> list[int]:
    eligible = []
    for index, name in enumerate(header[1:], start=1):
        wavelength = parse_number(name)
        if wavelength is not None and 1000.0 <= wavelength <= 2500.0:
            eligible.append(index)
    if not eligible:
        raise ValueError("No numeric wavelengths found between 1000 and 2500 nm")
    if len(eligible) <= maximum:
        return eligible
    positions = np.linspace(0, len(eligible) - 1, maximum, dtype=int)
    return [eligible[position] for position in positions]


def read_aligned_subset(
    dataset_dir: Path, recipe: Recipe
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    targets: dict[str, float] = {}
    with (dataset_dir / "Y.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if not reader.fieldnames or recipe.target_column not in reader.fieldnames:
            raise KeyError(f"Target {recipe.target_column!r} is absent from {dataset_dir / 'Y.csv'}")
        for row in reader:
            value = parse_number(row[recipe.target_column])
            if value is not None:
                targets[row["observation_id"]] = value

    spectra: list[list[float]] = []
    response: list[float] = []
    with (dataset_dir / "X.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter=";")
        header = next(reader)
        selected = select_wavelengths(header)
        selected_header = [header[index] for index in selected]
        for row in reader:
            target = targets.get(row[0])
            if target is None:
                continue
            values = [parse_number(row[index]) for index in selected]
            if any(value is None for value in values):
                continue
            spectra.append([float(value) for value in values if value is not None])
            response.append(target)

    required = recipe.n_calibration + recipe.n_validation
    if len(response) < required:
        raise ValueError(
            f"{recipe.source_id} has only {len(response)} complete aligned rows; "
            f"{required} are required"
        )
    order = np.random.default_rng(recipe.seed).permutation(len(response))[:required]
    return np.asarray(spectra)[order], np.asarray(response)[order], selected_header


def write_matrix(path: Path, data: np.ndarray, header: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows((f"{value:.10g}" for value in row) for row in data)


def write_target(path: Path, data: np.ndarray, name: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([name])
        writer.writerows([f"{value:.10g}"] for value in data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        required=True,
        help="Directory containing the standardized nirs4all dataset folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "datasets",
    )
    args = parser.parse_args()

    for recipe in RECIPES:
        source_dir = args.datasets_dir.resolve() / recipe.source_id
        validate_redistribution(source_dir)
        spectra, response, wavelengths = read_aligned_subset(source_dir, recipe)
        split = recipe.n_calibration
        dataset_dir = args.output_dir / recipe.dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        write_matrix(dataset_dir / "Xcal.csv", spectra[:split], wavelengths)
        write_target(dataset_dir / "Ycal.csv", response[:split], recipe.target_label)
        write_matrix(dataset_dir / "Xval.csv", spectra[split:], wavelengths)
        write_target(dataset_dir / "Yval.csv", response[split:], recipe.target_label)
        print(
            f"{recipe.dataset_id}: {split} calibration + {len(response) - split} validation, "
            f"{spectra.shape[1]} wavelengths, {recipe.target_column} "
            f"{response.min():.3g}–{response.max():.3g}"
        )


if __name__ == "__main__":
    main()
