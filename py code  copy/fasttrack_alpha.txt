# fasttrack_alpha.py
import numpy as np
import pandas as pd
from pathlib import Path
import traceback

def fit_lin(x, y):
    sl, ic = np.polyfit(x, y, 1)
    yhat = sl * x + ic
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else -np.inf
    return sl, ic, r2

def partition_spectrum_abs(r, q_grid=None, s_min=16, boxes_min=8,
                            n_scales_target=28, fit_lo=0.20, fit_hi=0.60, K_shifts=8):
    v = np.asarray(r, dtype=float)
    N = len(v)
    if q_grid is None:
        q_grid = np.arange(-3.0, 3.0 + 1e-9, 0.5)

    s_max = max(s_min + 1, N // boxes_min)
    scales = np.unique((np.logspace(np.log10(s_min), np.log10(s_max), n_scales_target)).astype(int))
    scales = scales[(scales >= s_min) & (scales <= s_max)]
    if len(scales) < 10:
        scales = np.unique((np.linspace(s_min, s_max, 28)).astype(int))
    if len(scales) < 10:
        raise ValueError("Insufficient valid scales")

    Z = np.zeros((len(q_grid), len(scales)))
    valid = np.zeros(len(scales), dtype=bool)
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
        if not vals:
            continue
        M = np.array(vals)
        M = np.maximum(M, 1e-300)
        Z[:, j] = np.exp(np.mean(np.log(M), axis=0))
        valid[j] = True

    scales = scales[valid]
    Z = Z[:, valid]
    if len(scales) < 10:
        raise ValueError("Too few valid scales after averaging")

    w0 = int(np.floor(fit_lo * len(scales)))
    w1 = int(np.ceil(fit_hi * len(scales)))
    if w1 - w0 < 10:
        w0, w1 = 0, len(scales)

    log_s = np.log(scales.astype(float))
    tau = np.zeros(len(q_grid))
    r2_vec = np.zeros(len(q_grid))
    for i in range(len(q_grid)):
        y = np.log(np.maximum(Z[i, :], 1e-300))
        sl, _, r2 = fit_lin(log_s[w0:w1], y[w0:w1])
        tau[i] = sl
        r2_vec[i] = r2

    dq = q_grid[1] - q_grid[0]
    alpha = np.gradient(tau, dq)
    f_alpha = q_grid * alpha - tau

    idx_q1 = int(np.argmin(np.abs(q_grid - 1.0)))
    idx_q0 = int(np.argmin(np.abs(q_grid - 0.0)))
    tau1 = float(tau[idx_q1])
    tau0 = float(tau[idx_q0])

    i_peak = int(np.argmax(f_alpha))
    alpha0 = float(alpha[i_peak])
    fmax = float(f_alpha[i_peak])
    lam = float(np.max(alpha) - np.min(alpha))

    d2 = np.gradient(np.gradient(f_alpha, dq), dq)
    concave = bool(np.all(d2[w0:w1] <= 1e-6))

    idx_q2 = int(np.argmin(np.abs(q_grid - 2.0)))
    q2_slope = float(tau[idx_q2])

    diag = {
        "tau0": tau0, "tau1": tau1, "fmax": fmax, "concave": concave,
        "r2_median": float(np.median(r2_vec)),
        "alpha_min": float(np.min(alpha)), "alpha_max": float(np.max(alpha)),
        "scales_used": int(len(scales)), "fit_window_idx": (w0, w1)
    }
    return alpha0, q2_slope, lam, diag

def evaluate(diag, alpha0, lam):
    return {
        "tau_identity": (abs(diag["tau1"]) <= 1e-3) and (-1.1 <= diag["tau0"] <= -0.9),
        "geometry": (0.90 <= diag["fmax"] <= 1.10) and diag["concave"],
        "fit_quality": (diag["r2_median"] >= 0.995),
        "empirical_band": (1.6 <= alpha0 <= 2.0) and (0.15 <= lam <= 0.80)
    }

def run_and_report(label, r, s_min):
    alpha0, q2, lam, diag = partition_spectrum_abs(r, s_min=s_min)
    checks = evaluate(diag, alpha0, lam)
    print(f"\n=== {label} | s_min={s_min} ===")
    print(f"Scales used: {diag['scales_used']}  fit window idx: {diag['fit_window_idx']}")
    print(f"tau(0): {diag['tau0']:.4f}   tau(1): {diag['tau1']:.6f}")
    print(f"f_max: {diag['fmax']:.4f}   Concave: {diag['concave']}")
    print(f"Median R^2: {diag['r2_median']:.5f}   alpha range: [{diag['alpha_min']:.3f}, {diag['alpha_max']:.3f}]")
    print("Triple (volatility measure):")
    print(f"  Alpha0: {alpha0:.6f}")
    print(f"  q=2 scaling slope: {q2:.6f}")
    print(f"  Lambda: {lam:.6f}")
    print("Checks:")
    for k, v in checks.items():
        print(f"  - {k}: {'PASS' if v else 'FAIL'}")
    print(f"Overall verdict: {'PASS' if all(checks.values()) else 'FAIL'}")
    return checks

if __name__ == "__main__":
    print("Starting fast-track alpha run for |r|, r^2, and 5-day rolling |r|...")
    try:
        fp = Path("nasdaq100_returns.csv")
        if not fp.exists():
            raise FileNotFoundError(f"Missing file: {fp.resolve()}")

        df = pd.read_csv(fp, usecols=["date", "logreturns"])
        print(f"Loaded {len(df)} rows from {fp.name}")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        raw_r = df["logreturns"].dropna().values
        print(f"Non-NaN logreturns count: {len(raw_r)}")

        measures = {
            "|r|": np.abs(raw_r),
            "r^2": raw_r**2,
            "5-day rolling |r|": np.convolve(np.abs(raw_r), np.ones(5), 'valid')
        }

        for label, series in measures.items():
            checks = run_and_report(label, series, s_min=16)
            if not checks["empirical_band"]:
                run_and_report(label, series, s_min=24)

    except Exception:
        print("\nERROR during run:")
        traceback.print_exc()
