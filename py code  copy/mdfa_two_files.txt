# mdfa_two_files.py
# Multifractal Detrended Fluctuation Analysis (MFDFA) for two daily returns files.

import numpy as np
import pandas as pd
from pathlib import Path

# ---------- MFDFA core ----------
def _integrated_profile(x):
    x = np.asarray(x, dtype=float)
    x = x - np.mean(x)
    return np.cumsum(x)

def _poly_detrend(y, order=1):
    n = len(y)
    t = np.arange(n, dtype=float)
    coeffs = np.polyfit(t, y, order)
    trend = np.polyval(coeffs, t)
    return y - trend

def _segment_variances(profile, s, order):
    n = len(profile)
    ns = n // s
    if ns == 0:
        return np.array([])
    F2 = []
    # forward
    for v in range(ns):
        seg = profile[v*s:(v+1)*s]
        res = _poly_detrend(seg, order=order)
        F2.append(np.mean(res**2))
    # backward
    for v in range(ns):
        seg = profile[n - (v+1)*s : n - v*s]
        res = _poly_detrend(seg, order=order)
        F2.append(np.mean(res**2))
    return np.array(F2, dtype=float)

def mfdfa(x, q_grid, s_min=16, s_max_frac=0.125, n_scales=20, order=1):
    x = np.asarray(x, dtype=float)
    n = len(x)
    s_max = max(s_min+1, int(np.floor(n * s_max_frac)))
    scales = np.unique((np.logspace(np.log10(s_min), np.log10(s_max), n_scales)).astype(int))
    scales = scales[(scales >= s_min) & (scales <= s_max)]
    Y = _integrated_profile(x)
    Fq = np.zeros((len(q_grid), len(scales)), dtype=float)
    for j, s in enumerate(scales):
        F2 = _segment_variances(Y, s, order=order)
        F2 = F2[F2 > 0]
        if len(F2) == 0:
            Fq[:, j] = np.nan
            continue
        lnF2 = np.log(F2)
        for i, q in enumerate(q_grid):
            if np.isclose(q, 0.0):
                Fq[i, j] = np.exp(0.5 * np.mean(lnF2))
            else:
                m = np.mean(F2**(q/2.0))
                Fq[i, j] = m**(1.0/q)
    log_s = np.log(scales.astype(float))
    hq = np.zeros(len(q_grid), dtype=float)
    for i in range(len(q_grid)):
        y = np.log(np.maximum(Fq[i, :], 1e-300))
        good = np.isfinite(y)
        xs, ys = log_s[good], y[good]
        sl, _ = np.polyfit(xs, ys, 1)
        hq[i] = sl
    dq = q_grid[1] - q_grid[0]
    tau = q_grid * hq - 1.0
    dhdq = np.gradient(hq, dq)
    alpha = hq + q_grid * dhdq
    falpha = q_grid * alpha - tau
    i_peak = int(np.nanargmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.nanmax(alpha) - np.nanmin(alpha))
    return alpha0, lam

# ---------- Runner ----------
def load_returns(path, col="logreturns", use_abs=True):
    df = pd.read_csv(path)
    if col not in df.columns:
        raise ValueError(f"{path.name} must contain column '{col}'")
    r = pd.to_numeric(df[col], errors="coerce").dropna().values
    return np.abs(r) if use_abs else r

def run_file(path):
    series = load_returns(path, use_abs=True)
    q_grid = np.arange(-3.0, 3.0 + 1e-12, 0.5)
    alpha0, lam = mfdfa(series, q_grid=q_grid, s_min=16, s_max_frac=0.125, n_scales=20, order=1)
    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f}")

if __name__ == "__main__":
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")
    run_file(file1)
    run_file(file2)
