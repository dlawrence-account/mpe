#!/usr/bin/env python
"""
make_synthetic.py
Generate synthetic logreturn data with known regime boundaries for testing MPE+MaxEnt.

Outputs:
- data/synthetic_test.csv       : synthetic time series with 'date' and 'logreturns' columns
- data/synthetic_truth.json     : true regime boundary indices and dates
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

# --- Config ---
DATA_DIR = Path(__file__).parent / "data"
N_SEGMENTS = 3
SEGMENT_LENGTHS = [50, 50, 50]
START_DATE = "2024-01-01"
SEED = 42

# Regime parameters: (mean daily logreturn, daily volatility)
REGIMES = [
    (0.001, 0.01),
    (-0.0005, 0.015),
    (0.0008, 0.02)
]

def generate_regime(mu: float, sigma: float, length: int) -> np.ndarray:
    """Generate a logreturn series for a single regime."""
    return np.random.normal(loc=mu, scale=sigma, size=length)

def main():
    np.random.seed(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_logrets = []
    boundaries = []

    for idx, (length, (mu, sigma)) in enumerate(zip(SEGMENT_LENGTHS, REGIMES)):
        segment_logrets = generate_regime(mu, sigma, length)
        all_logrets.extend(segment_logrets)
        if idx < N_SEGMENTS - 1:
            boundaries.append(len(all_logrets) - 1)

    dates = pd.date_range(start=START_DATE, periods=len(all_logrets), freq="D")
    df = pd.DataFrame({
        "date": dates,           # lowercase 'date'
        "logreturns": all_logrets
    })

    # Schema check before saving
    expected_cols = ["date", "logreturns"]
    if list(df.columns) != expected_cols:
        raise ValueError(f"Schema mismatch: expected {expected_cols}, got {list(df.columns)}")

    csv_path = DATA_DIR / "synthetic_test.csv"
    df.to_csv(csv_path, index=False)

    truth = {
        "indices": boundaries,
        "boundaries": [df["date"].dt.strftime("%Y-%m-%d")[i] for i in boundaries]
    }
    truth_path = DATA_DIR / "synthetic_truth.json"
    with open(truth_path, "w") as f:
        json.dump(truth, f, indent=2)

    print(f"✅ Synthetic test data written to {csv_path.resolve()}")
    print(f"✅ Truth boundaries written to {truth_path.resolve()}")

if __name__ == "__main__":
    main()
