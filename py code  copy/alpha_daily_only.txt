# alpha_daily_only.py
# Input: CSV(s) with a 'logreturns' column (daily log returns).
# Output: Alpha0 (peak of f(α)) and Lambda (spectrum width) over the full sample.
# Method: Structure functions on daily squared returns (|r|^2), non-overlapping blocks,
#         m in [8, min(64, N//20)], q in [1.0, 4.0], mean moments.

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# -------- core helpers --------
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
        a = a[a > 0]  # keep logs finite
        if a.size == 0:
            continue
        # mean of |rm|^q (no median; no trimming by default)
        a_pow = a[:, None] ** q_grid[None, :]
        S[:, j] = np.mean(a_pow, axis=0)
    return S

def spectrum_from_zeta(q_grid, zeta):
    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(zeta, dq)          # dζ/dq
    tau   = zeta - 1.0                     # τ(q)
    falpha = 1.0 + q_grid*alpha - zeta     # f(α)
    return tau, alpha, falpha

def alpha_lambda_from_returns(logreturns,
                              qmin=1.0, qmax=4.0, dq=0.25,
                              m_min=8, m_max=None, n_m=16):
    # Build volatility-like daily measure from daily log returns only
    r = np.asarray(logreturns, dtype=float)
    measure = np.abs(r) ** 2  # |r|^2

    N = len(measure)
    if m_max is None:
        m_max = max(m_min + 1, min(64, N // 20))
    if m_max <= m_min:
        raise ValueError("Series too short for the chosen m range.")
    m_list = np.unique(np.round(np.logspace(np.log10(m_min), np.log10(m_max), n_m)).astype(int))

    q_grid = np.arange(qmin, qmax + 1e-12, dq)

    S = structure_functions(measure, q_grid, m_list)
    valid = np.all(np.isfinite(S), axis=0)
    if not np.any(valid):
        raise RuntimeError("No valid structure function points. Try reducing m_max.")
    m_used = m_list[valid]
    S = S[:, valid]
    logm = np.log(m_used.astype(float))

    # Fit ζ(q) over log m
    zeta = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(S[i, :], 1e-300))
        zeta[i] = linfit(logm, y)

    # Legendre transform
    tau, alpha, falpha = spectrum_from_zeta(q_grid, zeta)
    i_peak = int(np.argmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))
    concave = bool(np.all(np.gradient(np.gradient(falpha, dq)) <= 1e-6))

    return alpha0, lam, dict(concave=concave, m_min=int(m_used.min()), m_max=int(m_used.max()),
                             qmin=float(q_grid[0]), qmax=float(q_grid[-1]))

def run_file(path: Path):
    df = pd.read_csv(path)
    if "logreturns" not in df.columns:
        raise ValueError(f"{path.name} must contain 'logreturns'")
    lr = pd.to_numeric(df["logreturns"], errors="coerce").dropna().values
    alpha0, lam, diag = alpha_lambda_from_returns(lr)
    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f} | concave={diag['concave']}, m=[{diag['m_min']},{diag['m_max']}], q=[{diag['qmin']},{diag['qmax']}]")

if __name__ == "__main__":
    files = [Path(x) for x in sys.argv[1:]]
    if not files:
        # Defaults if none provided
        files = [Path("nasdaq100_returns.csv"), Path("ORCL 2015 to 2025.csv")]
    for p in files:
        run_file(p)
