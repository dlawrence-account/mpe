# alpha_two_files.py
import numpy as np
import pandas as pd
from pathlib import Path

def fit_lin(x, y):
    sl, ic = np.polyfit(x, y, 1)
    return sl

def partition_spectrum_abs(r, q_grid=None, s_min=16, boxes_min=8,
                            n_scales_target=28, fit_lo=0.20, fit_hi=0.60, K_shifts=8):
    v = np.abs(np.asarray(r, dtype=float))
    N = len(v)
    if q_grid is None:
        q_grid = np.arange(-3.0, 3.0 + 1e-9, 0.5)

    s_max = max(s_min + 1, N // boxes_min)
    scales = np.unique((np.logspace(np.log10(s_min), np.log10(s_max), n_scales_target)).astype(int))
    scales = scales[(scales >= s_min) & (scales <= s_max)]

    Z = np.zeros((len(q_grid), len(scales)))
    for j, s in enumerate(scales):
        vals = []
        for k in range(K_shifts):
            start = k
            n_boxes = (N - start) // s
            if n_boxes < boxes_min:
                continue
            seg = v[start:start + n_boxes * s]
            mass = np.add.reduceat(seg, np.arange(0, len(seg), s)).astype(float)
            mass = np.maximum(mass, 1e-300)
            mass = mass / np.sum(mass)
            Zk = np.empty(len(q_grid))
            for i, q in enumerate(q_grid):
                if np.isclose(q, 1.0):
                    Zk[i] = 1.0
                else:
                    Zk[i] = float(np.sum(mass ** q))
            vals.append(Zk)
        if vals:
            M = np.array(vals)
            M = np.maximum(M, 1e-300)
            Z[:, j] = np.exp(np.mean(np.log(M), axis=0))

    w0 = int(np.floor(fit_lo * len(scales)))
    w1 = int(np.ceil(fit_hi * len(scales)))
    log_s = np.log(scales.astype(float))
    tau = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(Z[i, :], 1e-300))
        tau[i] = fit_lin(log_s[w0:w1], y[w0:w1])

    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(tau, dq)
    alpha0 = float(alpha[np.argmax(q_grid * alpha - tau)])
    lam = float(np.max(alpha) - np.min(alpha))
    return alpha0, lam

def run_file(path):
    df = pd.read_csv(path, usecols=["logreturns"])
    r = df["logreturns"].dropna().values
    alpha0, lam = partition_spectrum_abs(r)
    print(f"{path.name}: Alpha0 = {alpha0:.6f}, Lambda = {lam:.6f}")

if __name__ == "__main__":
    # Point these to your two files
    file1 = Path("nasdaq100_returns.csv")
    file2 = Path("ORCL 2015 to 2025.csv")

    run_file(file1)
    run_file(file2)
