import numpy as np
import pandas as pd
from scipy.stats import genpareto
import argparse

def estimate_alpha_gpd(excesses: np.ndarray) -> float:
    """
    Fit GPD to excesses via scipy.stats.genpareto.fit
    Returns tail exponent alpha = 1/ξ.
    """
    ξ, loc, β = genpareto.fit(excesses, floc=0)
    return 1.0 / ξ

def main():
    parser = argparse.ArgumentParser(
        description="GPD tail‐index via scipy.stats.genpareto.fit with k‐sweep"
    )
    parser.add_argument("csv_file", help="CSV with 'date' and 'logreturns'")
    parser.add_argument(
        "--ks", type=int, nargs="+",
        default=[25, 50, 75, 100],
        help="List of k values (top |returns|) to sweep"
    )
    parser.add_argument(
        "--date_fmt", type=str, default="%m/%d/%y",
        help="Date format for parsing dates"
    )
    args = parser.parse_args()

    # Load and sort returns
    df = pd.read_csv(args.csv_file, usecols=["date", "logreturns"])
    df["date"] = pd.to_datetime(df["date"], format=args.date_fmt)
    R = np.abs(df.sort_values("date")["logreturns"].values)
    n = R.size

    print(f"{'k':>4s} {'alpha (1/ξ)':>12s} {'threshold u':>12s}")
    for k in args.ks:
        if k >= n:
            print(f"{k:4d} {'N/A':>12s} {'N/A':>12s}")
            continue
        tail = np.sort(R)[-k:]
        u = tail[0]
        excesses = tail - u
        try:
            alpha = estimate_alpha_gpd(excesses)
            print(f"{k:4d} {alpha:12.4f} {u:12.6f}")
        except Exception:
            print(f"{k:4d} {'ERROR':>12s} {u:12.6f}")

if __name__ == "__main__":
    main()
