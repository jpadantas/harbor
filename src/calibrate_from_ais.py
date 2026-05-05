"""
HARBOR AIS Calibration Script

This script analyzes AIS (Automatic Identification System) vessel tracking
data to derive empirical movement parameters for each vessel size category
(Small, Medium, Large). The parameters include:

  - Median speed (knots)
  - Speed standard deviation (knots)
  - Heading spread (degrees) — the angular variability of vessel courses

These calibrated parameters replace the hardcoded assumptions in harbor.py,
producing more realistic future-position heatmaps from SAR imagery.

Usage:
    python src/calibrate_from_ais.py --input data/AIS_Dataset.xlsx --output data/ais_calibration.json

The classification into Small / Medium / Large follows the vessel Length
field from the AIS data:
    - Small:  Length < 50 m
    - Medium: 50 m <= Length < 200 m
    - Large:  Length >= 200 m
"""

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

SHEET_NAME = "raw-ais-data"

# Vessel size thresholds (based on real-world Length in the AIS record).
# These mirror the conceptual categories in harbor.py but use physical
# dimensions rather than pixel-based bounding-box areas.
SMALL_MAX_LENGTH = 50       # metres  (exclusive)
MEDIUM_MAX_LENGTH = 200     # metres  (exclusive)

# Default / fallback values identical to the original harbor.py hardcodes.
DEFAULT_PARAMS = {
    "Small":  {"speed_knots": 6,  "speed_std": 3.0,  "spread_deg": 30, "sample_count": 0},
    "Medium": {"speed_knots": 10, "speed_std": 4.0,  "spread_deg": 25, "sample_count": 0},
    "Large":  {"speed_knots": 15, "speed_std": 5.0,  "spread_deg": 20, "sample_count": 0},
}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate HARBOR movement priors from AIS data."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the AIS Excel dataset (.xlsx).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("data", "ais_calibration.json"),
        help=(
            "Path where the calibration JSON will be written "
            "(default: data/ais_calibration.json)."
        ),
    )
    parser.add_argument(
        "--min-points",
        type=int,
        default=5,
        help="Minimum AIS data points per MMSI to be included (default: 5).",
    )
    return parser.parse_args()


def _load_ais(filepath: str) -> pd.DataFrame:
    """Load and clean the AIS dataset."""
    print(f"[1/5] Loading AIS data from: {filepath}")
    df = pd.read_excel(filepath, sheet_name=SHEET_NAME)

    required = ["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "Heading", "Length"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["BaseDateTime"] = pd.to_datetime(df["BaseDateTime"], errors="coerce")

    # Decode compacted AIS fields (same logic as the notebook)
    df["lat_deg"]     = df["LAT"] / 100_000.0
    df["lon_deg"]     = df["LON"] / 100_000.0
    df["sog_knots"]   = df["SOG"] / 10.0
    df["cog_deg"]     = df["COG"] / 10.0
    df["heading_deg"] = df["Heading"] / 10.0

    # AIS special / unavailable values
    df.loc[df["heading_deg"] >= 511.0, "heading_deg"] = pd.NA
    df.loc[df["sog_knots"]   >= 102.3, "sog_knots"]   = pd.NA
    df.loc[df["cog_deg"]     >= 360.0, "cog_deg"]      = pd.NA

    # Basic sanity filters
    df = df.dropna(subset=["MMSI", "BaseDateTime", "lat_deg", "lon_deg"])
    df = df[
        df["lat_deg"].between(-90, 90) &
        df["lon_deg"].between(-180, 180)
    ].copy()

    # Decode Length (AIS stores it as integer, usually in metres already
    # but check for compacted format — if all values are > 1000 divide by 10)
    if df["Length"].median() > 1000:
        df["length_m"] = df["Length"] / 10.0
    else:
        df["length_m"] = df["Length"].astype(float)

    df = df.sort_values(["MMSI", "BaseDateTime"]).reset_index(drop=True)

    print(f"      Loaded {len(df)} records for {df['MMSI'].nunique()} unique vessels.")
    return df


def _classify_size(length_m: float) -> Optional[str]:
    """Classify a vessel into Small / Medium / Large by length."""
    if pd.isna(length_m) or length_m <= 0:
        return None
    if length_m < SMALL_MAX_LENGTH:
        return "Small"
    if length_m < MEDIUM_MAX_LENGTH:
        return "Medium"
    return "Large"


def _angular_diff(a: float, b: float) -> float:
    """Shortest signed angular difference between two headings (degrees)."""
    d = b - a
    d = (d + 180) % 360 - 180
    return abs(d)


def _compute_stats(
    df: pd.DataFrame, min_points: int
) -> Dict[str, Dict]:
    """
    For every MMSI with enough data points, compute:
      - median SOG  (speed proxy)
      - std-dev of consecutive COG differences (heading spread proxy)

    Then aggregate by size category.
    """
    print("[3/5] Computing per-vessel statistics …")

    category_speeds:  Dict[str, List[float]] = {"Small": [], "Medium": [], "Large": []}
    category_spreads: Dict[str, List[float]] = {"Small": [], "Medium": [], "Large": []}

    grouped = df.groupby("MMSI")
    n_used = 0

    for mmsi, group in grouped:
        if len(group) < min_points:
            continue

        # Determine vessel size category from the most common Length value
        lengths = group["length_m"].dropna()
        if lengths.empty:
            continue
        representative_length = lengths.median()
        cat = _classify_size(representative_length)
        if cat is None:
            continue

        # Speed: median of reported SOG (knots)
        sog_values = group["sog_knots"].dropna()
        if sog_values.empty:
            continue
        # Filter out stationary vessels (SOG ~ 0) to get "underway" speed
        sog_moving = sog_values[sog_values > 0.5]
        if sog_moving.empty:
            continue
        median_speed = float(sog_moving.median())
        category_speeds[cat].append(median_speed)

        # Heading spread: std-dev of consecutive COG differences
        cog_values = group["cog_deg"].dropna().values
        if len(cog_values) >= 2:
            diffs = [_angular_diff(cog_values[i], cog_values[i+1])
                     for i in range(len(cog_values) - 1)]
            if diffs:
                spread = float(np.std(diffs))
                category_spreads[cat].append(spread)

        n_used += 1

    print(f"      Analysed {n_used} vessels with >= {min_points} points.")
    return category_speeds, category_spreads


def _aggregate(
    speeds: Dict[str, List[float]],
    spreads: Dict[str, List[float]],
) -> Dict[str, Dict]:
    """
    Aggregate per-vessel statistics into per-category parameters.
    Falls back to DEFAULT_PARAMS when a category has no data.
    """
    print("[4/5] Aggregating per-category parameters …")
    result = {}

    for cat in ("Small", "Medium", "Large"):
        sp_list = speeds.get(cat, [])
        sd_list = spreads.get(cat, [])

        if sp_list:
            speed = round(float(np.median(sp_list)), 2)
            speed_std = round(float(np.std(sp_list)), 2)
        else:
            speed = DEFAULT_PARAMS[cat]["speed_knots"]
            speed_std = DEFAULT_PARAMS[cat]["speed_std"]

        if sd_list:
            spread = round(float(np.median(sd_list)), 2)
        else:
            spread = DEFAULT_PARAMS[cat]["spread_deg"]

        sample_count = len(sp_list)

        result[cat] = {
            "speed_knots": speed,
            "speed_std": speed_std,
            "spread_deg": spread,
            "sample_count": sample_count,
        }

        status = "calibrated" if sample_count > 0 else "DEFAULT (no data)"
        print(f"      {cat:8s}: speed={speed:6.2f} kn  "
              f"(std={speed_std:.2f})  spread={spread:5.2f} deg  "
              f"n={sample_count}  [{status}]")

    return result


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    print("=" * 50)
    print(" HARBOR -- AIS Calibration Pipeline")
    print("=" * 50)
    print(f"Input       : {args.input}")
    print(f"Output      : {args.output}")
    print(f"Min points  : {args.min_points}")
    print()

    # 1. Load
    df = _load_ais(args.input)

    # 2. Classify
    print("[2/5] Classifying vessels by size …")
    df["size_category"] = df["length_m"].apply(_classify_size)
    counts = df.dropna(subset=["size_category"]).groupby("size_category")["MMSI"].nunique()
    for cat in ("Small", "Medium", "Large"):
        n = counts.get(cat, 0)
        print(f"      {cat:8s}: {n} unique vessels")

    # 3–4. Statistics & aggregation
    speeds, spreads = _compute_stats(df, args.min_points)
    calibration = _aggregate(speeds, spreads)

    # 5. Write output
    print(f"[5/5] Writing calibration to: {args.output}")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fp:
        json.dump(calibration, fp, indent=2, ensure_ascii=False)

    print()
    print("Done. Calibration file saved successfully.")


if __name__ == "__main__":
    main()
