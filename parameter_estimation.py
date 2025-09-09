#!/usr/bin/env python3
"""
parameter_estimation_ChatGPT.py
Multifractal parameter estimation (alpha_core, alpha_far-tail, H, lambda)
Refactored for speed with robust CSV loading and timing breakdowns.
"""

import sys
import csv
import time
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import linregress, levy_stable
from scipy.optimize import curve_fit, minimize

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

    print("--- Aggregated data preview (first 10 rows) ---")
    if len(out_df) > 0:
        print(out_df.head(10).to_string(index=False))
    else:
        print("(no rows)")
    print(f"Total rows after aggregation (STEP={step}): {len(out_df)}")
    print(f"[Timing] Aggregation: {time.time() - t0:.3f} s")
    print("------------------------------------------------\n")

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
    popt, _ = curve_fit(
        zeta_model, q_use, zeta_use,
    popt, _ = curve_fit(
        zeta_model, q_use, zeta_use,
        p0=[H_guess, 0.1],
        bounds=([0.0, 0.0], [2.0, 5.0]),
        maxfev=20000
    )
    print(f"[Timing] MF-DFA: {time.time() - t0:.3f} s")
    return float(popt[0]), float(popt[1])

# ------------------------
# Alpha estimation (ECF + Powell-bounded MLE refinement)
# ------------------------
def ecf_alpha(returns):
    t0 = time.time()
    x = returns - np.median(returns)
    s = np.std(x)
    if s == 0 or not np.isfinite(s):
        print(f"[Timing] Alpha (ECF only): {time.time() - t0:.3f} s")
        return 2.0, 1.0
    t_min = 0.1 / s
    t_max = 1.0 / s
    m = 32
    t = np.linspace(t_min, t_max, m)
    phi_hat = np.exp(1j * np.outer(t, x)).mean(axis=1)
    mod_phi = np.clip(np.abs(phi_hat), 1e-12, 1 - 1e-12)
    y = np.log(-np.log(mod_phi))
    X = np.log(t)
    slope, intercept, _, _, _ = linregress(X, y)
    alpha_hat = float(np.clip(slope, 1.0, 2.0))
    gamma_hat = float(np.exp(intercept / alpha_hat))
    print(f"[Timing] Alpha (ECF): {time.time() - t0:.3f} s")
    return alpha_hat, gamma_hat

def refine_alpha_mle_powell(returns, alpha_init, gamma_fixed):
    t0 = time.time()
    x = returns - np.median(returns)
    x = x[np.isfinite(x)]
    if x.size == 0:
        print(f"[Timing] Alpha (MLE skip): {time.time() - t0:.3f} s")
        return float(alpha_init)

    def nll(a_arr):
        a = float(a_arr[0])
        if a <= 0.99 or a >= 2.01:
            return np.inf
        try:
            ll = levy_stable.logpdf(x, a, 0.0, loc=0.0, scale=gamma_fixed)
            ll = ll[np.isfinite(ll)]
            if ll.size == 0:
                return np.inf
            return -np.sum(ll)
        except Exception:
            return np.inf

    res = minimize(
        nll,
        x0=np.array([alpha_init], dtype=float),
        method="Powell",
        bounds=[(1.0, 2.0)],
        options={"xtol": 1e-3, "maxiter": 800, "disp": False}
    )
    a_ref = float(res.x[0] if res.success else alpha_init)
    print(f"[Timing] Alpha (MLE Powell): {time.time() - t0:.3f} s")
    return a_ref

def estimate_core_alpha(returns, use_mle):
    t0 = time.time()
    lo, hi = np.percentile(returns, [5, 95])
    ecf_data = returns[(returns >= lo) & (returns <= hi)]
    if ecf_data.size < 64:
        ecf_data = returns
    alpha_ecf, gamma_ecf = ecf_alpha(ecf_data)
    if use_mle:
        alpha_final = refine_alpha_mle_powell(returns, alpha_ecf, gamma_ecf)
    else:
        alpha_final = alpha_ecf
    print(f"[Timing] Alpha (total): {time.time() - t0:.3f} s")
    return alpha_final

# ------------------------
# Far-tail alpha (Hill-like)
# ------------------------
def estimate_far_tail_alpha(returns, k_frac=0.05):
    t0 = time.time()
    abs_r = np.abs(returns[np.isfinite(returns)])
    abs_r = abs_r[abs_r > 0]
    if abs_r.size < 10:
        print(f"[Timing] Far-tail: {time.time() - t0:.3f} s")
        return float("nan")
    k = max(5, int(abs_r.size * k_frac))
    topk = np.partition(abs_r, -k)[-k:]
    xmin = np.min(topk)
    if not np.isfinite(xmin) or xmin <= 0:
        print(f"[Timing] Far-tail: {time.time() - t0:.3f} s")
        return float("nan")
    alpha_hat = 1.0 / (np.mean(np.log(topk)) - np.log(xmin))
    print(f"[Timing] Far-tail: {time.time() - t0:.3f} s")
    return alpha_hat

# ------------------------
# Range runner
# ------------------------
def run_for_range(df, start_date, end_date, use_mle):
    mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))
    rets = df.loc[mask, "DailyLogReturns"].values.astype(float)
    rets = rets[np.isfinite(rets)]
    if rets.size == 0:
        print(f"No data in range {start_date} to {end_date}")
        return float("nan"), float("nan"), float("nan"), float("nan")

    H, lam = estimate_h_and_lambda(rets)
    alpha_core = estimate_core_alpha(rets, use_mle=use_mle)
    alpha_ft = estimate_far_tail_alpha(rets)

    if np.isfinite(alpha_core) and alpha_core < 1.5:
        print(f"  [Warning] alpha={alpha_core:.4f} < 1.5")
    if np.isfinite(H) and H < 0.5:
        print(f"  [Warning] H={H:.4f} < 0.5")

    return alpha_core, alpha_ft, H, lam

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    t_all = time.time()

    df_clean = load_and_clean_returns()
    df_used = aggregate_returns(df_clean, STEP)

    if df_used.empty:
        print("No data available after aggregation. Skipping analysis.")
        sys.exit(0)

    # Full range
    print("=== Full-range analysis ===")
    alpha_core, alpha_ft, H, lam = run_for_range(
        df_used, df_used["Date"].min(), df_used["Date"].max(), use_mle=USE_MLE_REFINEMENT
    )
    print(f"Full     {alpha_core:.4f} {alpha_ft:.4f} {H:.4f} {lam:.4f}\n")

    # K regimes
    n = len(df_used)
    if K > 1 and n > 0:
        print(f"=== {K} regime analysis ===")
        chunk_size = n // K
        for i in range(K):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < K - 1 else n
            if end_idx - start_idx <= 1:
                continue
            start_date = df_used["Date"].iloc[start_idx]
            end_date = df_used["Date"].iloc[end_idx - 1]
            alpha_core, alpha_ft, H, lam = run_for_range(
                df_used, start_date, end_date, use_mle=USE_MLE_REFINEMENT
            )
            print(
                f"Regime{i+1} ({start_date.date()} to {end_date.date()}) "
                f"{alpha_core:.4f} {alpha_ft:.4f} {H:.4f} {lam:.4f}"
            )

    print(f"\n(total runtime: {time.time() - t_all:.2f} seconds)")
