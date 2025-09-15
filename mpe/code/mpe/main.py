#!/usr/bin/env python
"""
Main entry point for MPE pipeline with MaxEnt segmentation.

Assumes:
- Input CSV is placed in data/input/
- CSV has columns: date (parseable), logreturns (numeric)
- No price-to-return conversion is done here.

The newest CSV in data/input/ is automatically selected.
"""

import argparse
import json
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd
from .maxent import run_maxent

# Standard input/output directories (relative to repo root)
INPUT_DIR = Path(__file__).parents[3] / "data" / "input"
OUTPUT_DIR = Path(__file__).parents[3] / "data" / "output"

def find_latest_csv() -> Path:
    """Find the most recently modified CSV in INPUT_DIR."""
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")
    files = list(INPUT_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {INPUT_DIR}")
    return max(files, key=lambda f: f.stat().st_mtime)

def segment_lengths(boundaries: List[int], n: int) -> List[int]:
    """Compute segment lengths from boundary indices and total length n."""
    if n <= 0:
        return []
    edges = [-1] + boundaries + [n - 1]
    return [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]

def main():
    parser = argparse.ArgumentParser(description="Run MPE pipeline with MaxEnt segmentation")
    parser.add_argument("--instrument", required=True, help="Instrument type label (e.g., equity)")
    parser.add_argument("--triple", nargs=3, type=float, required=True, metavar=("A", "B", "C"),
                        help="Triple parameters (three floats)")
    parser.add_argument("--k", type=int, required=True, help="Number of regimes for segmentation")
    args = parser.parse_args()

    # Locate latest CSV in standard location
    csv_path = find_latest_csv()
    print(f"📄 Using latest CSV: {csv_path.name}")

    # Load and validate
    df = pd.read_csv(csv_path, parse_dates=["date"])
    if "date" not in df.columns or "logreturns" not in df.columns:
        raise ValueError("CSV must contain 'date' and 'logreturns' columns")

    series = df["logreturns"].to_numpy(dtype=float)
    n = len(series)
    if n < max(2, args.k):
        raise ValueError(f"Not enough data points ({n}) for k={args.k}")

    # Run MaxEnt segmentation
    seg = run_maxent(series, k=args.k)
    boundaries = sorted(int(i) for i in seg.get("boundaries", []) if 0 <= i < n - 1)

    # Prepare output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    iso_dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    boundary_dates = [iso_dates[i] for i in boundaries]
    lengths = segment_lengths(boundaries, n=n)

    results = {
        "indices": boundaries,
        "boundaries": boundary_dates
    }
    results_file = OUTPUT_DIR / "segmentation_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    # Basic stats on provided logreturns
    mean_lr = float(np.nanmean(series))
    vol_lr = float(np.nanstd(series))

    # Human-readable segment spans
    starts = [0] + [b + 1 for b in boundaries]
    ends = boundaries + [n - 1]
    segments_human = [(iso_dates[s], iso_dates[e]) for s, e in zip(starts, ends)]

    # Print summary
    print("\n=== MPE Pipeline Results ===")
    print(f"Stats:   {{'mean_logreturn': {mean_lr}, 'volatility': {vol_lr}}}")
    print(f"MaxEnt:  {{'num_segments': {len(boundaries) + 1}, "
          f"'segments': {segments_human}, 'lengths': {lengths}}}")
    print("============================\n")
    print(f"✅ Segmentation results written to {results_file.resolve()}")

if __name__ == "__main__":
    main()
