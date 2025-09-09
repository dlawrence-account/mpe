#!/usr/bin/env python3
"""
parameter_estimation_ChatGPT.py
Refactored for speed with timing breakdowns.
"""

import sys
import csv
import time
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import linregress, levy_stable
from scipy.optimize import curve_fit, minimize_scalar

# ------------------------
# Prompts
# ------------------------
file_input = input("Enter CSV file name [default=nasdaq100_returns.csv]: ").strip()
CSV_FILE = file_input if file_input else "nasdaq100_returns.csv"

step_input = input("Enter sampling interval STEP [default=1]: ").strip()
STEP = int(step_input) if step_input else 1

k_input = input("Enter number of regimes K [default=1]: ").strip()
K = int(k_input) if k_input else 1

mle_input = input("Use MLE refinement for alpha? [default=yes]: ").strip().lower()
USE_MLE_REFINEMENT = False if mle_input in ("n", "no") else True

# ------------------------
# Robust CSV loader
# ------------------------
def load_and_clean_returns():
    t0 = time.time()
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        print(f"ERROR: File '{CSV_FILE}' not found.")
        sys.exit(1)

    df = pd.read_csv(
        CSV_FILE,
        engine="python",
        sep=",",
        quoting=csv.QUOTE_NONE
    )

    df = df.dropna(axis=1, how="all")
    df.columns = [c.strip().strip('"') for c in df.columns]

    rename_map = {}
    for c in df.columns:
        key = c.lower().replace(" ", "")
        if key == "date":
            rename_map[c] = "Date"
        elif key == "logreturns":
            rename_map[c] = "LogReturns"
    df = df.rename(columns=rename_map)

    for col in ["Date", "LogReturns"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.strip('"')

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", infer_datetime_format=True)
    df["LogReturns"] = pd.to_numeric(df["LogReturns"], errors="coerce")

    df = df.dropna(subset=["Date", "LogReturns"]).sort_values("Date").reset_index(drop=True)

    if df.empty:
        print(f"ERROR: No valid rows found in '{CSV_FILE}'.")
        if raw_lines:
            print("First raw line from file:", raw_lines[0].strip())
        sys.exit(1)

    clean_name = Path(CSV_FILE).with_name(Path(CSV_FILE).stem + "_clean.csv")
    df.to_csv(clean_name, index=False)

    print("\n--- Data preview (first 10 rows) ---")
    print(df.head(10).to_string(index=False))
    print(f"Total rows loaded: {len(df)}")
    print(f"[Timing] Load & clean: {time.time() - t0:.3f} s")
    print("------------------------------------\n")

    return df

# ------------------------
# Aggregation
# ------------------------
def aggregate_returns(df, step=1):
    t0 = time.time()
    if step <= 1:
        out_df = df.rename(columns={"LogReturns": "DailyLogReturns"})
    else:
        n = len(df)
        m = (n // step) * step
        if m == 0:
            out_df = pd.DataFrame(columns=["Date", "DailyLogReturns"])
        else:
            dates = df["Date"].values[:m].reshape(-1, step)[:, -1]
            sums = df["LogReturns"].values[:m].reshape(-1, step).sum(axis=1)
            out_df = pd.DataFrame({"Date": dates, "DailyLogReturns": sums})
    fname = Path(CSV_FILE).stem + f"_step{step}.csv"
    out_df.to_csv(fname, index=False)
    print(f"[Timing] Aggregation: {time.time() - t0:.3f} s")
    return out_df

# ------------------------
# MF-DFA (fast)
# ------------------------
def _mse_detrended_linear(segments):
    if segments.size == 0:
        return np.array([])
    nseg, s = segments.shape
    t = np.arange(s, dtype=float)
    t_mean = (s - 1) / 2.0
    t_centered = t - t_mean
    denom = np.dot(t_centered, t_centered)
    y_mean = segments.mean(axis=1, keepdims=True)
    y_centered = segments - y_mean
    cov_ty = y_centered @ t_centered
    slope = cov_ty / denom
    intercept = y_mean.squeeze(-1) - slope * t_mean
    fit = slope[:, None] * t[None, :] + intercept[:, None]
    resid = segments - fit
    mse = np.mean(resid * resid, axis=1)
    return mse

def _fqs_from_mse(mse, q_vals):
    mse = mse[np.isfinite(mse) & (mse > 0)]
    if mse.size == 0:
        return np.full_like(q_vals, np.nan, dtype=float)
    Fq = np.empty_like(q_vals, dtype=float)
    log_mse = np.log(mse)
    for i, q in enumerate(q_vals):
        if q == 0.0:
            Fq[i] = np.exp(0.5 * np.mean(log_mse))
        else:
            Fq[i] = (np.mean(mse ** (q / 2.0))) ** (1.0 / q)
    return Fq

def mfdfa_fast(returns, scales, q_vals):
    x = np.asarray(returns, dtype=float)
    if x.size < np.max(scales) * 4:
        return np.full_like(q_vals, np.nan, dtype=float)
    profile = np.cumsum(x - np.mean(x))
    log_s = []
    log_Fq_per_s = []
    for s in scales:
        nseg = len(profile) // s
        if nseg < 4:
            continue
        forward = profile[:nseg * s].reshape(nseg, s)
        backward = profile[-nseg * s:].reshape(nseg, s)
        mse_all = np.concatenate([_mse_detrended_linear(forward),
                                  _mse_detrended_linear(backward)], axis=0)
        Fq = _fqs_from_mse(mse_all, q_vals)
        if np.all(~np.isfinite(Fq)):
            continue
        log_s.append(np.log(s))
        log_Fq_per_s.append(np.log(Fq))
    if not log_s:
        return np.full_like(q_vals, np.nan, dtype=float)
    log_s = np.array(log_s)
    log_Fq_per_s = np.vstack(log_Fq_per_s)
    hq = np.empty_like(q_vals, dtype=float)
    for j in range(len(q_vals)):
        y = log_Fq_per_s[:, j]
        mask = np.isfinite(y)
        if mask.sum() < 2:
            hq[j] = np.nan
        else:
            slope, _, _, _, _ = linregress(log_s[mask], y[mask])
            hq[j] = slope
    return hq

def estimate_h_and_lambda(returns):
    t0 = time.time()
    scales = np.array([10, 20, 40, 80, 160, 250])
    q_vals = np.array([0.5, 1.0, 2.0, 3.0, 4.0])
    hq = mfdfa_fast(returns, scales, q_vals)
    idx2 = np.where(q_vals == 2.0)[0][0]
    H_guess = float(hq[idx2]) if np.isfinite(hq[idx2]) else 0.5
    zeta = q_vals * hq - 1.0
    valid = np.isfinite(zeta)
    q_use = q_vals[valid]
    zeta_use = zeta[valid]
    if len(q_use) < 3:
        print(f"[Timing] MF-DFA: {time.time() - t0:.3f} s")
        return float(np.nan_to_num(H_guess, nan=0.5)), 0.0
    def zeta_model(q, Hfit, lam):
        return q * Hfit - 0.5 * (lam ** 2) * (q ** 2 - q)
    popt, _ = curve_fit(zeta_model, q_use, zeta_use,
                        p0=[H_guess, 0.1],
                        bounds=([0.0, 0.0], [2.0, 5.0]),
                        maxfev=20000)
    print(f"[Timing] MF-DFA: {time.time()