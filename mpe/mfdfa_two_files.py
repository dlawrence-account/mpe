# mfdfa_two_files.py
# Multifractal Detrended Fluctuation Analysis (MFDFA) for two daily returns files.
# Outputs: Alpha0 (peak of f(α)) and Lambda (spectrum width) for each file.

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
    # Fit polynomial trend and return residuals
    coeffs = np.polyfit(t, y, order)
    trend = np.polyval(coeffs, t)
    return y - trend

def _segment_variances(profile, s, order):
    n = len(profile)
    ns = n // s
    if ns == 0:
        return np.array([])
    # Use 2*ns segments: forward and backward (standard MFDFA trick)
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

def mfdfa(x, q_grid=None, s_min=16, s_max_frac=0.125, n_scales=20, order=1):
    # x is the signal to analyze (use |returns| for volatility)
    x = np.asarray(x, dtype=float)
    n = len(x)
    if q_grid is None:
        q_grid = np.arange(-3.0, 3.0 + 1e-12, 0.5)

    # Build scales s (window sizes)
    s_max = max(s_min+1, int(np.floor(n * s_max_frac)))
    if s_max <= s_min + 1:
        raise ValueError("Series too short for chosen scales.")
    scales = np.unique((np.logspace(np.log10(s_min), np.log10(s_max), n_scales)).astype(int))
    scales = scales[(scales >= s_min) & (scales <= s_max)]
    if len(scales) < 8:
        raise ValueError("Insufficient number of scales. Adjust s_min/s_max_frac.")

    # Integrated profile
    Y = _integrated_profile(x)

    # Compute Fq(s) for each q and s
    Fq = np.zeros((len(q_grid), len(scales)), dtype=float)
    for j, s in enumerate(scales):
        F2 = _segment_variances(Y, s, order=order)
        F2 = F2[F2 > 0]
        if len(F2) == 0:
            Fq[:, j] = np.nan
            continue
        # Handle q != 0 and q = 0 separately
        lnF2 = np.log(F2)
        for i, q in enumerate(q_grid):
            if np.isclose(q, 0.0):
                # geometric mean -> exp( (1/2M) * sum log(F2) )^{1/2} => exp(0.5 * mean(log F2))
                Fq[i, j] = np.exp(0.5 * np.mean(lnF2))
            else:
                # ( (1/2M) * sum F2^{q/2} )^{1/q}
                m = np.mean(F2**(q/2.0))
                Fq[i, j] = m**(1.0/q)

    # Fit log Fq(s) ~ h(q) * log s + c
    log_s = np.log(scales.astype(float))
    hq = np.zeros(len(q_grid), dtype=float)
    r2 = np.zeros(len(q_grid), dtype=float)
    for i in range(len(q_grid)):
        y = np.log(np.maximum(Fq[i, :], 1e-300))
        good = np.isfinite(y)
        xs, ys = log_s[good], y[good]
        if len(xs) < 6:
            hq[i] = np.nan
            r2[i] = np.nan
            continue
        sl, ic = np.polyfit(xs, ys, 1)
        hq[i] = sl
        # simple R^2 diag
        yhat = sl*xs + ic
        ss_res = np.sum((ys - yhat)**2)
        ss_tot = np.sum((ys - np.mean(ys))**2)
        r2[i] = 1 - ss_res/ss_tot if ss_tot > 0 else np.nan

    # Multifractal spectrum via Legendre transform
    # tau(q) = q*h(q) - 1 (time series convention)
    dq = q_grid[1] - q_grid[0]
    tau = q_grid * hq - 1.0
    # alpha(q) = d tau / d q = h(q) + q * h'(q)
    dhdq = np.gradient(hq, dq)
    alpha = hq + q_grid * dhdq
    # f(alpha) = q*alpha - tau
    falpha = q_grid * alpha - tau

    # Derive alpha0 at peak f(α), and lambda as width
    i_peak = int(np.nanargmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.nanmax(alpha) - np.nanmin(alpha))

    # Basic diagnostics if you want to inspect
    diag = {
        "scales_used": int(len(scales)),
        "s_min": int(scales.min()),
        "s_max": int(scales.max()),
        "median_R2_hq": float(np.nanmedian(r2)),
        "concave": bool(np.all(np.gradient(np.gradient(falpha, dq), dq)[np.isfinite(falpha)] <= 1e-6)),
        "alpha_min": float(np.nanmin(alpha)),
        "alpha_max": float(np.nanmax(alpha)),
    }
    return alpha0, lam, diag

# ---------- Runner for two files ----------

def load_returns(path, col="logreturns", use_abs=True):
    df = pd.read_csv(path)
    if col not in df.columns:
        raise ValueError(f"{path.name} must contain column '{col}'")
    r = pd.to_numeric(df[col], errors="coerce").dropna().values
    return np.abs(r) if use_abs else r

def run_file(path, use_abs=True, qmin=-3.0, qmax=3.0, dq=0.5, s_min=16, s_max_frac=0.125, n_scales=20, order=1):
    series = load_returns(path, use_abs=use_abs)
    q_grid = np.arange(qmin, qmax + 1e-12, dq)
    alpha0, lam, diag = mfdfa(series, q_grid=q_grid, s_min=s_min, s_max_frac=s_max_frac, n_scales=n_scales, order=order)
    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f}  | scales: {diag['scales_used']} ({diag['s_min']}..{diag['s_max']}), median R^2(h): {diag['median_R2_hq']:.4f}, concave: {diag['concave']}")
    return alpha0, lam, diag

if __name__ == "__main__":
    # Edit these two filenames as needed
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")

    # Use |returns| (volatility proxy) at daily frequency
    run_file(file1, use_abs=True)
    run_file(file2, use_abs=True)
