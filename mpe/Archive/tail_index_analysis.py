import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import genpareto
import argparse

def plot_empirical_tail(returns):
    x = np.sort(returns[returns > 0])
    n = len(x)
    S = 1.0 - np.arange(1, n+1) / n
    plt.figure(figsize=(6,4))
    plt.loglog(x, S, marker='.', linestyle='none')
    plt.xlabel("Absolute return")
    plt.ylabel("Survival probability")
    plt.title("Empirical tail on log–log scale")
    plt.grid(True, which='both', ls='--', lw=0.5)
    plt.show()

def fit_gpd_alpha(excess):
    ξ, loc, β = genpareto.fit(excess, floc=0)
    return ξ, β, 1.0/ξ

def bootstrap_alpha(excess, n_boot=500):
    alphas = []
    for _ in range(n_boot):
        sample = np.random.choice(excess, size=len(excess), replace=True)
        ξ, _, _ = genpareto.fit(sample, floc=0)
        alphas.append(1.0/ξ)
    return np.mean(alphas), np.percentile(alphas, [2.5, 97.5])

def main():
    parser = argparse.ArgumentParser(
        description="Tail‐index analysis with visual threshold and GPD fitting"
    )
    parser.add_argument("csv_file", help="CSV file with 'date' and 'logreturns'")
    parser.add_argument("--date_fmt", default="%m/%d/%y",
                        help="Date format for parsing (default %m/%d/%y)")
    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.csv_file, usecols=["date", "logreturns"])
    df["date"] = pd.to_datetime(df["date"], format=args.date_fmt)
    returns = np.abs(df.sort_values("date")["logreturns"].values)

    # Step 1: Plot empirical tail
    plot_empirical_tail(returns)

    # Step 2: Prompt for threshold u
    u = float(input("Enter tail threshold u based on plot: ").strip())
    tail = returns[returns > u]
    excess = tail - u
    if len(excess) < 20:
        print(f"Warning: only {len(excess)} exceedances—fit may be unstable.")

    # Step 3: Fit GPD and compute α
    ξ, β, alpha = fit_gpd_alpha(excess)
    print(f"\nFitted GPD parameters:")
    print(f"  Threshold u       : {u:.6f}")
    print(f"  Number of excesses: {len(excess)}")
    print(f"  GPD shape ξ       : {ξ:.4f}")
    print(f"  GPD scale β       : {β:.6f}")
    print(f"  Tail exponent α   : {alpha:.4f}")

    # Step 4: Bootstrap confidence interval
    mean_alpha, ci = bootstrap_alpha(excess)
    print(f"\nBootstrap α mean  : {mean_alpha:.4f}")
    print(f"Bootstrap 95% CI  : [{ci[0]:.4f}, {ci[1]:.4f}]")

if __name__ == "__main__":
    main()
