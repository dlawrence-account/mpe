# sf_alpha_two_files_fixed.py
# Structure functions on daily |returns| with overlapping aggregation.
# Uses (trimmed) mean moments to avoid the median degeneracy (λ=0).
# Outputs: Alpha0 (peak of f(α)) and Lambda (spectrum width) for each CSV.

import numpy as np
import pandas as pd
from pathlib import Path

# ---------- helpers ----------
def linfit(x, y):
    sl, ic = np.polyfit(x, y, 1)
    return sl

def aggregate_overlapping(x, m):
    # Sum over m-day overlapping windows
    n = len(x)
    if n < m:
        return np.array([])
    csum = np.cumsum(np.insert(x, 0, 0.0))
    return csum[m:] - csum[:-m]

def trimmed_mean(a, q=0.01):
    if a.size == 0:
        return np.nan
    if q <= 0.0:
        return float(np.mean(a))
    lo, hi = np.quantile(a, [q, 1.0 - q])
    a = a[(a >= lo) & (a <= hi)]
    return float(np.mean(a)) if a.size else np.nan

def structure_functions(abs_r, q_grid, m_list, overlap=True, trim=0.01):
    # Returns S[q_index, m_index] = E(|sum_{i=1..m} r_i|^q) estimated via (trimmed) mean
    S = np.full((len(q_grid), len(m_list)), np.nan, dtype=float)
    for j, m in enumerate(m_list):
        rm = aggregate_overlapping(abs_r, m) if overlap else \
             abs_r[:(len(abs_r)//m)*m].reshape(-1, m).sum(axis=1)
        if rm.size == 0:
            continue
        a = np.abs(rm)
        a = a[a > 0]  # avoid zeros in logs
        if a.size == 0:
            continue
        for i, q in enumerate(q_grid):
            vals = a**q
            S[i, j] = trimmed_mean(vals, q=trim)
    return S

def spectrum_from_zeta(q_grid, zeta):
    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(zeta, dq)            # dζ/dq
    tau   = zeta - 1.0                       # τ(q)
    falpha = 1.0 + q_grid*alpha - zeta       # f(α)
    return tau, alpha, falpha

# ---------- main runner ----------
def run_file(path,
             qmin=0.5, qmax=3.5, dq=0.25,          # stable daily q-range
             m_min=1, m_max=None, n_m=18,          # log-spaced horizons
             overlap=True, trim=0.01):             # 1% trim stabilizes heavy tails
    df = pd.read_csv(path)
    if "logreturns" not in df.columns:
        raise ValueError(f"{path.name} must contain a 'logreturns' column")
    r = pd.to_numeric(df["logreturns"], errors="coerce").dropna().values
    abs_r = np.abs(r)

    N = len(abs_r)
    if m_max is None:
        m_max = max(m_min + 1, min(128, N // 10))
    m_list = np.unique(np.round(np.logspace(np.log10(m_min), np.log10(m_max), n_m)).astype(int))

    q_grid = np.arange(qmin, qmax + 1e-12, dq)

    S = structure_functions(abs_r, q_grid, m_list, overlap=overlap, trim=trim)
    valid = np.all(np.isfinite(S), axis=0)
    if not np.any(valid):
        raise RuntimeError("No valid structure function points. Try smaller m_max or trim=0.0.")
    m_used = m_list[valid]
    S = S[:, valid]
    logm = np.log(m_used.astype(float))

    # Fit ζ(q) for each q
    zeta = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(S[i, :], 1e-300))
        zeta[i] = linfit(logm, y)

    # Build spectrum
    tau, alpha, falpha = spectrum_from_zeta(q_grid, zeta)
    i_peak = int(np.argmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))

    # Simple curvature check (should be concave)
    concave = bool(np.all(np.gradient(np.gradient(falpha, dq)) <= 1e-6))

    print(
        f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f} "
        f"| concave={concave}, m range=[{m_used.min()},{m_used.max()}], q range=[{q_grid[0]},{q_grid[-1]}], trim={trim}"
    )
    return alpha0, lam

if __name__ == "__main__":
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")
    run_file(file1)
    run_file(file2)
