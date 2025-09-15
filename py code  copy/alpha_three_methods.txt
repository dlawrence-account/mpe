# alpha_three_methods.py
# Input: CSV(s) with 'logreturns' column (daily)
# Output: Pareto–Lévy alpha estimates from:
#   1. Clauset–Shalizi–Newman MLE (auto x_min)
#   2. Hill estimator (auto k via stability)
#   3. Log–log rank–size OLS (same tail as CSN)

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ---------- 1. CSN MLE ----------
def csn_mle_alpha(data):
    """Return alpha, x_min, n_tail using Clauset–Shalizi–Newman method."""
    x = np.sort(np.abs(data))
    n = len(x)
    ks_best = np.inf
    alpha_best = None
    x_min_best = None
    n_tail_best = None
    for i in range(n - 1):
        x_min = x[i]
        tail = x[i:]
        if len(tail) < 50:  # need enough tail points
            break
        alpha = 1 + len(tail) / np.sum(np.log(tail / x_min))
        # Empirical CDF of tail
        cdf_emp = np.arange(len(tail)) / float(len(tail))
        # Theoretical CDF for Pareto(alpha, x_min)
        cdf_theor = 1 - (tail / x_min) ** (-alpha)
        ks = np.max(np.abs(cdf_emp - cdf_theor))
        if ks < ks_best:
            ks_best = ks
            alpha_best = alpha
            x_min_best = x_min
            n_tail_best = len(tail)
    return alpha_best, x_min_best, n_tail_best

# ---------- 2. Hill estimator ----------
def hill_alpha(data):
    """Hill estimator with automatic k via stability window."""
    x = np.sort(np.abs(data))[::-1]  # descending
    n = len(x)
    hill_estimates = []
    ks = range(10, min(n // 10, 500))  # candidate k values
    for k in ks:
        topk = x[:k]
        hill_est = k / np.sum(np.log(topk / x[k]))
        hill_estimates.append(hill_est)
    hill_estimates = np.array(hill_estimates)
    # Stability: pick k with minimal std dev in a ±5 window
    stability = []
    for i in range(len(ks)):
        lo = max(0, i - 5)
        hi = min(len(ks), i + 6)
        stability.append(np.std(hill_estimates[lo:hi]))
    k_best = ks[int(np.argmin(stability))]
    alpha_best = hill_estimates[int(np.argmin(stability))]
    return alpha_best, k_best

# ---------- 3. Rank–size OLS ----------
def rank_size_alpha(data, x_min):
    """OLS slope on log–log CCDF above x_min."""
    tail = np.abs(data)
    tail = tail[tail >= x_min]
    tail_sorted = np.sort(tail)[::-1]
    ranks = np.arange(1, len(tail_sorted) + 1)
    logx = np.log(tail_sorted)
    logrank = np.log(ranks)
    slope, intercept = np.polyfit(logx, logrank, 1)
    alpha = -slope
    return alpha, len(tail_sorted)

# ---------- Runner ----------
def run_file(path):
    df = pd.read_csv(path)
    if "logreturns" not in df.columns:
        raise ValueError(f"{path.name} must contain 'logreturns'")
    r = pd.to_numeric(df["logreturns"], errors="coerce").dropna().values

    # 1. CSN MLE
    alpha_csn, xmin_csn, n_tail_csn = csn_mle_alpha(r)

    # 2. Hill
    alpha_hill, k_hill = hill_alpha(r)

    # 3. Rank–size OLS using CSN's xmin
    alpha_rs, n_tail_rs = rank_size_alpha(r, xmin_csn)

    print(f"\n=== {path.name} ===")
    print(f"CSN MLE:       alpha = {alpha_csn:.6f}, x_min = {xmin_csn:.6g}, tail n = {n_tail_csn}")
    print(f"Hill (auto k): alpha = {alpha_hill:.6f}, k = {k_hill}")
    print(f"Rank–size OLS: alpha = {alpha_rs:.6f}, tail n = {n_tail_rs}")

if __name__ == "__main__":
    files = [Path(x) for x in sys.argv[1:]] or [
        Path("nasdaq100_returns.csv"),
        Path("ORCL 2015 to 2025.csv")
    ]
    for f in files:
        run_file(f)
