# debug-raw-parameters.py
print("ESTIMATING MAPM PARAMETERS ON RAW DAILY RETURNS")

import pandas as pd
import numpy as np
from scipy.stats import linregress
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# Load raw daily log returns
df = pd.read_csv("nasdaq100_returns.csv", parse_dates=["Date"])
rets = df["DailyLogReturns"].values
N = len(rets)
print(f"✓ Loaded {N} daily returns from {df['Date'].min().date()} to {df['Date'].max().date()}")

# 1. Hurst exponent via DFA (q=2)
def estimate_hurst_dfa(returns, s_min=10, s_max=None):
    if s_max is None or s_max > len(returns)//4:
        s_max = len(returns)//4
    scales = np.unique(np.logspace(np.log10(s_min), np.log10(s_max), num=20, dtype=int))
    F2 = []
    X = np.cumsum(returns - np.mean(returns))
    for s in scales:
        segments = len(X)//s
        rms = []
        for v in range(segments):
            seg = X[v*s:(v+1)*s]
            t = np.arange(s)
            # linear detrend
            p = np.polyfit(t, seg, 1)
            fit = np.polyval(p, t)
            rms.append(np.sqrt(np.mean((seg - fit)**2)))
        F2.append(np.mean(rms))
    slope, _, _, _, _ = linregress(np.log(scales), np.log(F2))
    return slope

H = estimate_hurst_dfa(rets)
print(f"✓ Hurst exponent H ≈ {H:.3f}")

# 2. Intermittency λ via curvature of ζ(q)
def estimate_lambda_via_zeta(returns, lags=None):
    if lags is None:
        lags = np.arange(10, len(returns)//4, 20)
    qs = np.array([0.5, 1.0, 1.5, 2.0])
    zeta = []
    for q in qs:
        S = []
        for tau in lags:
            diffs = np.abs(returns[tau:] - returns[:-tau])**q
            S.append(np.mean(diffs))
        slope, _, _, _, _ = linregress(np.log(lags), np.log(S))
        zeta.append(slope)
    # Fit zeta(q) = q*H - (lam^2/2)*(q^2 - q)
    coeffs = np.polyfit(qs**2 - qs, np.array(qs)*H - np.array(zeta), 1)
    lam = np.sqrt(max(0.0, coeffs[0]*2))
    return lam

lam = estimate_lambda_via_zeta(rets)
print(f"✓ Intermittency λ ≈ {lam:.3f}")

# 3. Core tail index α via central fit (5–95% quantiles)
def estimate_core_alpha(returns, lower=5, upper=95):
    sub = np.percentile(returns, [lower, upper])
    mask = (returns >= sub[0]) & (returns <= sub[1])
    data = returns[mask]
    # Hill on absolute values
    r = np.sort(np.abs(data))
    k = max(50, int(len(r)*0.10))
    tail = r[-k:]
    logs = np.log(tail)
    return 1.0/np.mean(logs - logs[0])

alpha = estimate_core_alpha(rets)
print(f"✓ Core tail index α ≈ {alpha:.3f}")

# 4. Far-tail α_ft via Hill on top 5%
def estimate_far_tail_alpha(returns, tail_frac=0.05):
    r = np.sort(np.abs(returns))
    k = int(len(r)*tail_frac)
    tail = r[-k:]
    logs = np.log(tail)
    return 1.0/np.mean(logs - logs[0])

alpha_ft = estimate_far_tail_alpha(rets)
print(f"✓ Far-tail α_ft ≈ {alpha_ft:.3f}")

print("\nRAW PARAMETER ESTIMATION COMPLETE")
