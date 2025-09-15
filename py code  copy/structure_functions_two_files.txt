# structure_functions_two_files.py
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

def structure_functions(abs_r, q_grid, m_list, use_median=True):
    S = np.zeros((len(q_grid), len(m_list)))
    for j, m in enumerate(m_list):
        rm = aggregate_nonoverlap(abs_r, m)
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
    alpha = np.gradient(zeta, dq)           # dζ/dq
    tau = zeta - 1.0                        # τ(q)
    falpha = 1.0 + q_grid*alpha - zeta      # f(α)
    return tau, alpha, falpha

def run_file(path, qmin=0.5, qmax=3.0, dq=0.25):
    df = pd.read_csv(path)
    if "logreturns" not in df.columns:
        raise ValueError(f"{path.name} must contain a 'logreturns' column")
    r = pd.to_numeric(df["logreturns"], errors="coerce").dropna().values
    abs_r = np.abs(r)

    q_grid = np.arange(qmin, qmax + 1e-12, dq)
    m_list = np.unique(np.round(np.logspace(np.log10(1), np.log10(64), 16)).astype(int))

    S = structure_functions(abs_r, q_grid, m_list, use_median=True)
    valid = np.all(np.isfinite(S), axis=0)
    m_used = m_list[valid]
    S = S[:, valid]
    logm = np.log(m_used.astype(float))

    zeta = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(S[i, :], 1e-300))
        zeta[i] = linfit(logm, y)

    tau, alpha, falpha = spectrum_from_zeta(q_grid, zeta)
    i_peak = int(np.argmax(falpha))
    alpha0 = float(alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))
    concave = bool(np.all(np.gradient(np.gradient(falpha, dq)) <= 1e-6))

    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f}, concave={concave}, m range=[{m_used.min()},{m_used.max()}]")
    return alpha0, lam

if __name__ == "__main__":
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")
    run_file(file1)
    run_file(file2)
