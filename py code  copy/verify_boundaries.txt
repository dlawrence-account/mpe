#!/usr/bin/env python
"""
verify_boundaries.py

Verification script for MPE+MaxEnt segmentation.

Modes:
- Synthetic mode: If synthetic_truth.json exists in data/, compare detected boundaries to truth.
- Real-data mode: If no truth file, just print detected boundaries in a verification-style table.

Assumes:
- Detected boundaries are in data/output/segmentation_results.json
- Synthetic truth (if present) is in data/synthetic_truth.json
- Input CSV (synthetic or real) is in data/input/ (latest file is used for mapping indices to dates)
- CSV schema must be: date,logreturns
"""

import json
from pathlib import Path
import pandas as pd

# Standard locations
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "output"
TRUTH_FILE = BASE_DIR / "data" / "synthetic_truth.json"
RESULTS_FILE = OUTPUT_DIR / "segmentation_results.json"
TOLERANCE_DAYS = 5
EXPECTED_COLUMNS = ["date", "logreturns"]

def find_latest_csv() -> Path:
    """Find the most recently modified CSV in INPUT_DIR."""
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")
    files = list(INPUT_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {INPUT_DIR}")
    return max(files, key=lambda f: f.stat().st_mtime)

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r") as f:
        return json.load(f)

def check_schema(df: pd.DataFrame):
    """Ensure DataFrame has the expected columns in the correct order."""
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"CSV schema mismatch.\nExpected: {EXPECTED_COLUMNS}\nFound:    {list(df.columns)}"
        )

def main():
    # Load detected boundaries
    results_data = load_json(RESULTS_FILE)
    detected_indices = results_data["indices"]

    # Load CSV to map indices -> dates
    csv_path = find_latest_csv()
    df = pd.read_csv(csv_path, parse_dates=["date"])
    check_schema(df)  # enforce schema before proceeding

    date_list = df["date"].dt.date.tolist()
    detected_dates = [date_list[i] for i in detected_indices]

    print("\n=== Verification ===")

    if TRUTH_FILE.exists():
        # Synthetic mode
        truth_data = load_json(TRUTH_FILE)
        true_indices = truth_data["indices"]
        true_dates = [date_list[i] for i in true_indices]

        offsets = []
        for i, td in enumerate(true_dates):
            if i < len(detected_dates):
                offsets.append((detected_dates[i] - td).days)
            else:
                offsets.append(None)

        print(f"True boundaries (index): {true_indices}")
        print(f"Detected boundaries (index): {detected_indices}")
        print(f"Offsets (days): {offsets}")

        if all(o is not None and abs(o) <= TOLERANCE_DAYS for o in offsets):
            print(f"✅ All boundaries within ±{TOLERANCE_DAYS} days of truth")
        else:
            print(f"⚠️ Some boundaries exceed ±{TOLERANCE_DAYS} days")

    else:
        # Real-data mode
        print("No synthetic truth file found — running in real-data mode.")
        print(f"Detected boundaries (index): {detected_indices}")
        print(f"Detected boundaries (dates): {[d.strftime('%Y-%m-%d') for d in detected_dates]}")
        print("Segments:")
        starts = [0] + [i + 1 for i in detected_indices]
        ends = detected_indices + [len(df) - 1]
        for s, e in zip(starts, ends):
            print(f"  {date_list[s]} → {date_list[e]}  (length {e - s + 1})")

    print("====================\n")

if __name__ == "__main__":
    main()
