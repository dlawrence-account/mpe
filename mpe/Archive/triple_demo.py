#!/usr/bin/env python3
"""
triple_demo.py
Two analysis functions:
  - mfdfa_on_returns(series)
  - volatility_measure_spectrum(series)
Plus optional CLI for single-file testing.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import traceback

from MFDFA import MFDFA  # make sure the MFDFA package is installed

# ----------------------------
# Utility: linear fit with R²
# ----------------------------
def fit_lin(xi, yi):
    slope, intercept = np.polyfit(xi, yi, 1)
    yhat = slope * xi + intercept
    ss_res = np.sum((yi - yhat) ** 2)
    ss_tot = np.sum((yi - np.mean(yi)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else -np.inf
    return slope, intercept, r2

# ----------------------------
# MF-DFA on signed returns
# ----------------------------
def mfdfa_on_returns(series, q_grid=None, order=1):
    if q_grid is None:
        q_grid = np.linspace(-5, 5, 21)
    N = len(series)
    lag = np.unique(np.logspace(0.5, np.log10(max(16, N // 8)), 40, dtype=int))
    lag = lag[(lag >= 5) & (lag <= N // 10)]

    lag_used, F = MFDFA(series, lag=lag, q=q_grid, order=order)

    if F.shape[0] == len(q_grid):
        q_actual = q_grid
    else:
        q_actual = np.linspace(q_grid.min(), q_grid.max(), F.shape[1])

    # Auto-select scaling window using q=2 with slope filter
    log_lag = np.log(lag_used)
    n = len(log_lag)
    edge = max(1, int(0.30 * n))
    cand_idx = np.arange(edge, n - edge) if (n - 2 * edge) >= 8 else np.arange(0, n)
    min_window = max(6, int(0.30 * len(cand_idx)))

    idx_q2 = (np.abs(q_actual - 2)).argmin()
    if F.shape[0] == len(q_actual):
        log_F_q2 = np.log(F[idx_q2])
    else:
        log_F_q2 = np.log(F[:, idx_q2])

    candidates = []
    for i in range(0, len(cand_idx) - min_window + 1):
        for j in range(i + min_window, len(cand_idx) + 1):
            s = cand_idx[i]
            e = cand_idx[j - 1] + 1
            sl, ic, r2 = fit_lin(log_lag[s:e], log_F_q2[s:e])
            candidates.append((r2, sl, s, e))
    candidates.sort(key=lambda x: (x[0], x[3] - x[2]), reverse=True)

    best = None
    for r2, sl, s, e in candidates:
        if 0.48 <= sl <= 0.52:
            best = (r2, sl, s, e)
            break
    if best is None:
        best = candidates[0]
        print("WARNING: returns MF-DFA: no window met tight H filter; using best R².")

    r2_best, H_est, i_start, i_end = best

    # h(q)
    h_q = []
    for i in range(len(q_actual)):
        if F.shape[0] == len(q_actual):
            log_F = np.log(F[i])
        else:
            log_F = np.log(F[:, i])
        sl, _, _ = fit_lin(log_lag[i_start:i_end], log_F[i_start:i_end])
        h_q.append(sl)
    h_q = np.array(h_q)

    # τ(q), α(q), f(α)
    dq = q_actual[1] - q_actual[0]
    tau_q = q_actual * h_q - 1
    alpha_q = np.gradient(tau_q, dq)
    f_alpha_q = q_actual * alpha_q - tau_q

    alpha0 = alpha_q[np.argmax(f_alpha_q)]
    lam = np.max(alpha_q) - np.min(alpha_q)

    return {"alpha0": alpha0, "H": H_est, "lambda": lam}

# ----------------------------
# Volatility-measure spectrum
# ----------------------------
def volatility_measure_spectrum(series, q_grid=None, n_scales=18):
    v = np.abs(series).astype(float)
    N = len(v)

    s_min = 8
    s_max = max(s_min + 1, N // 12)
    scales = np.unique((np.logspace(np.log10(s_min), np.log10(s_max), n_scales)).astype(int))
    scales = scales[scales >= s_min]
    if len(scales) < 6:
        scales = np.unique((np.linspace(s_min, s_max, 12)).astype(int))

    if q_grid is None:
        q_grid = np.linspace(-5, 5, 21)

    Z = np.zeros((len(q_grid), len(scales)))
    for j, s in enumerate(scales):
        n_boxes = N // s
        if n_boxes < 4:
            continue
        mass = np.add.reduceat(v[:n_boxes * s], np.arange(0, n_boxes * s, s))
        mass = np.maximum(mass, 1e-300)
        mass = mass / np.sum(mass)
        for i, q in enumerate(q_grid):
            if np.isclose(q, 1.0):
                Z[i, j] = np.exp(np.sum(mass * np.log(mass)))
            else:
                Z[i, j] = np.sum(mass ** q)

    log_s = np.log(scales.astype(float))
    w0, w1 = int(0.2 * len(scales)), int(0.85 * len(scales))
    if w1 - w0 < 6:
        w0, w1 = 0, len(scales)

    tau = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(Z[i, :], 1e-300))
        sl, _, r2 = fit_lin(log_s[w0:w1], y[w0:w1])
        tau[i] = sl

    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(tau, dq)
    f_alpha = q_grid * alpha - tau

    alpha0 = alpha[np.argmax(f_alpha)]
    lam = np.max(alpha) - np.min(alpha)

    # "Hurst-like" slope for q=2 on the measure
    idx_q2 = (np.abs(q_grid - 2)).argmin()
    y_q2 = np.log(np.maximum(Z[idx_q2, :], 1e-300))
    H_like, _, r2_q2 = fit_lin(log_s[w0:w1], y_q2[w0:w1])

    return {"alpha0": alpha0, "H": H_like, "lambda": lam}

# ----------------------------
# CLI for single-file testing
# ----------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compute multifractal triples for a single CSV.")
    ap.add_argument("--file", required=True, help="CSV with columns: date,logreturns")
    ap.add_argument("--date_fmt", default="%m/%d/%y", help="Date format in CSV")
    args = ap.parse_args()

    try:
        df = pd.read_csv(args.file, usecols=["date", "logreturns"])
        df["date"] = pd.to_datetime(df["date"], format=args.date_fmt)
        series = df["logreturns"].dropna().values

        res_r = mfdfa_on_returns(series)
        res_m = volatility_measure_spectrum(series)

        print("\n=== MF-DFA on returns ===")
        print(f"Alpha0: {res_r['alpha0']:.6f}")
        print(f"Hurst:  {res_r['H']:.6f}")
        print(f"Lambda: {res_r['lambda']:.6f}")

        print("\n=== Volatility measure spectrum ===")
        print(f"Alpha0: {res_m['alpha0']:.6f}")
        print(f"Hurst-like slope (q=2): {res_m['H']:.6f}")
        print(f"Lambda: {res_m['lambda']:.6f}")

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
