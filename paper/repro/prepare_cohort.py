#!/usr/bin/env python3
"""Resolve a frozen cohort manifest against an explicit local dataset root."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PATH_COLUMNS = ("train_path", "test_path", "ytrain_path", "ytest_path")


def resolve_data_path(raw: str, data_root: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    parts = path.parts
    if "data" in parts:
        parts = parts[parts.index("data") + 1 :]
    return data_root.joinpath(*parts).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()

    data_root = args.data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise SystemExit(f"dataset root not found: {data_root}")

    with args.input.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(column not in reader.fieldnames for column in PATH_COLUMNS):
            raise SystemExit(f"cohort path columns are incomplete: {args.input}")
        rows = list(reader)
        fieldnames = reader.fieldnames

    missing: list[Path] = []
    for row in rows:
        for column in PATH_COLUMNS:
            resolved = resolve_data_path(row[column], data_root)
            row[column] = str(resolved)
            if row.get("status", "ok").strip().lower() == "ok" and not resolved.is_file():
                missing.append(resolved)

    if missing:
        preview = "\n".join(f"  - {path}" for path in missing[:20])
        suffix = f"\n  ... and {len(missing) - 20} more" if len(missing) > 20 else ""
        raise SystemExit(f"{len(missing)} required cohort files are missing:\n{preview}{suffix}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"prepared {len(rows)} cohort rows -> {args.output}")


if __name__ == "__main__":
    main()
