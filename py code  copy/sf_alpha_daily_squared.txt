# sf_alpha_daily_squared.py
# Structure functions on daily squared returns to estimate measure-based alpha.
# Outputs: Alpha0 (peak of f(α)) and Lambda (spectrum width) for each CSV.

import numpy as np
import pandas as pd
from pathlib import Path

def linfit(x, y):
    sl, ic = np.polyfit(x, y, 1)
    return sl

def aggregate_nonoverlap(x, m):
    n = len(x) // m
    if n == 0:
        return np.array([])
    return x[:n*m].reshape(n, m).sum(axis=1)

def structure_functions(measure, q_grid, m_list):
    S = np.full((len(q_grid), len(m_list)), np.nan, dtype=float)
    for j, m in enumerate(m_list):
        rm = aggregate_nonoverlap(measure, m)
        if rm.size == 0:
            continue
        a = np.abs(rm)
        a = a[a > 0]  # avoid zeros in logs
        if a.size == 0:
            continue
        for i, q in enumerate(q_grid):
            S[i, j] = float(np.mean(a**q))  # mean (not median)
    return S

def spectrum_from_zeta(q_grid, zeta):
    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(zeta, dq)            # dζ/dq
    tau   = zeta - 1.0                       # τ(q)
    falpha = 1.0 + q_grid*alpha - zeta       # f(α)
    return tau, alpha, falpha

def run_file(path,
             qmin=1.0, qmax=4.0, dq=0.25,
             m_min=4, m_max=None, n_m=16):
    df = pd.read_csv(path)
    if "logreturns" not in df.columns:
        raise ValueError(f"{path.name} must contain 'logreturns'")
    r = pd.to_numeric(df["logreturns"], errors="coerce").dropna().values

    # Volatility-like measure for daily data
    measure = np.abs(r)**2

    N = len(measure)
    if m_max is None:
        m_max = max(m_min + 1, min(64, N // 20))
    m_list = np.unique(np.round(np.logspace(np.log10(m_min), np.log10(m_max), n_m)).astype(int))

    q_grid = np.arange(qmin, qmax + 1e-12, dq)

    S = structure_functions(measure, q_grid, m_list)
    valid = np.all(np.isfinite(S), axis=0)
    if not np.any(valid):
        raise RuntimeError("No valid structure function points. Try smaller m_max.")
    m_used = m_list[valid]
    S = S[:, valid]
    logm = np.log(m_used.astype(float))

    # Fit ζ(q) for each q
    zeta = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(S[i, :], 1e-300))
        zeta[i] = linfit(logm, y)

    # Legendre transform to spectrum
    tau, alpha, falpha = spectrum_from_zeta(q_grid, zeta)
    i_peak = int(np.argmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))

    # Minimal shape diagnostics
    concave = bool(np.all(np.gradient(np.gradient(falpha, dq)) <= 1e-6))
    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f} | concave={concave}, m=[{m_used.min()},{m_used.max()}], q=[{q_grid[0]},{q_grid[-1]}]")
    return alpha0, lam

if __name__ == "__main__":
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")
    run_file(file1)
    run_file(file2)
