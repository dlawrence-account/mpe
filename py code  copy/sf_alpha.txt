# sf_alpha.py — structure-function multifractal on daily data
import numpy as np, pandas as pd
from pathlib import Path

def linfit(x, y):
    sl, ic = np.polyfit(x, y, 1)
    yhat = sl * x + ic
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else -np.inf
    return sl, ic, r2

def aggregate_returns(r, m):
    # non-overlapping blocks to avoid dependence bias; try overlapping as robustness
    n = len(r) // m
    if n == 0: return np.array([])
    return r[:n*m].reshape(n, m).sum(axis=1)

def structure_function(r, q_grid, m_list, agg='nonoverlap', use_median=True):
    S = np.zeros((len(q_grid), len(m_list)))
    for j, m in enumerate(m_list):
        if agg == 'overlap':
            rm = np.convolve(r, np.ones(m), 'valid')
        else:
            rm = aggregate_returns(r, m)
        if rm.size == 0:
            S[:, j] = np.nan
            continue
        a = np.abs(rm)
        a = a[a > 0]
        for i, q in enumerate(q_grid):
            vals = a**q
            S[i, j] = np.median(vals) if use_median else np.mean(vals)
    return S

def spectrum_from_zeta(q_grid, zeta):
    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(zeta, dq)  # dζ/dq
    tau = zeta - 1.0               # τ(q) for time-series convention
    falpha = 1.0 + q_grid*alpha - zeta
    return tau, alpha, falpha

if __name__ == "__main__":
    fp = Path("nasdaq100_returns.csv")
    df = pd.read_csv(fp, usecols=["date", "logreturns"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    r = df["logreturns"].dropna().values

    # Config
    q_grid = np.arange(0.5, 3.0 + 1e-12, 0.25)  # avoid negatives for robustness on daily
    m_list = np.unique(np.round(np.logspace(np.log10(1), np.log10(64), 16)).astype(int))
    # Use absolute returns as magnitude
    series = np.abs(r)

    # Structure functions and zeta
    S = structure_function(series, q_grid, m_list, agg='nonoverlap', use_median=True)
    valid = np.all(np.isfinite(S), axis=0)
    m_used = m_list[valid]; S = S[:, valid]
    logm = np.log(m_used.astype(float))

    zeta = np.zeros(len(q_grid)); r2s = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(S[i, :], 1e-300))
        sl, _, r2 = linfit(logm, y)
        zeta[i] = sl
        r2s[i] = r2

    tau, alpha, falpha = spectrum_from_zeta(q_grid, zeta)
    i_peak = int(np.argmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))
    concave = bool(np.all(np.gradient(np.gradient(falpha, q_grid[1]-q_grid[0])) <= 1e-6))
    fmax = float(np.max(falpha))

    print(f"Scales m used: {len(m_used)} (min={m_used.min()}, max={m_used.max()})")
    print(f"Median R^2 across q (ζ fits): {np.median(r2s):.5f}")
    print(f"τ(0): {tau[np.argmin(np.abs(q_grid-0.0))] if np.any(q_grid==0.0) else 'n/a'}  τ(1): {float((zeta[q_grid.searchsorted(1.0)]-1.0) if (q_grid.min()<=1.0<=q_grid.max()) else 'n/a')}")
    print(f"f_max: {fmax:.4f}   Concave f(α): {concave}")
    print(f"alpha range: [{np.min(alpha):.3f}, {np.max(alpha):.3f}]")
    print("\nTriple (structure function):")
    print(f"Alpha0: {alpha0:.6f}")
    print(f"Lambda: {lam:.6f}")
