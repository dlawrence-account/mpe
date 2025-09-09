print("SCRIPT STARTED!")  # This line confirms the script begins

import numpy as np
import pandas as pd
from datetime import datetime

DATE_FORMAT = "%m/%d/%y"

def load_and_price(csv_path, sample_step=1):
    """
    Load CSV with daily log returns, compute price series,
    sample every `sample_step` rows, and calculate weekly log returns.
    """
    df = pd.read_csv(
        csv_path,
        parse_dates=['Date'],
        date_format=DATE_FORMAT
    )
    print("\nLoaded raw dataframe head:")
    print(df.head())
    df = df.sort_values('Date').reset_index(drop=True)
    df['Price'] = 100 * np.exp(df['DailyLogReturns'].cumsum())
    df_s = df.iloc[::sample_step].copy().reset_index(drop=True)
    df_s['WeeklyReturn'] = np.log(df_s['Price']) - np.log(df_s['Price'].shift(1))
    print("\nWeeklyReturn head:")
    print(df_s['WeeklyReturn'].head())
    return df_s

def compute_structure_functions(returns, q_list, tau_max):
    """
    Structure functions S_q(tau) = E[|r(t+tau) - r(t)|^q]
    """
    Sq = {q: [] for q in q_list}
    for tau in range(1, tau_max+1):
        diffs = np.abs(returns[tau:] - returns[:-tau])
        for q in q_list:
            Sq[q].append(np.mean(diffs**q))
    return {q: np.array(Sq[q]) for q in q_list}

def estimate_scaling_exponents(Sq, q_list):
    """
    Estimate τ(q) scaling exponents via regression.
    """
    from scipy import stats
    taus = np.arange(1, len(next(iter(Sq.values()))) + 1)
    log_taus = np.log(taus)
    tau_q = {}
    for q in q_list:
        slope, _, _, _, _ = stats.linregress(log_taus, np.log(Sq[q]))
        tau_q[q] = slope
    return tau_q

def fit_multifractal_spectrum(tau_q, q_list):
    """
    Fit singularity (f(α)) spectrum.
    """
    q_vals = np.array(q_list)
    tau_vals = np.array([tau_q[q] for q in q_list])
    dtau_dq = np.gradient(tau_vals, q_vals)
    alpha = dtau_dq
    f_alpha = q_vals * alpha - tau_vals
    idx_0 = np.argmax(f_alpha)
    alpha_min = np.min(alpha)
    alpha_max = np.max(alpha)
    alpha_0 = alpha[idx_0]
    f_alpha_0 = f_alpha[idx_0]
    delta_alpha = alpha_max - alpha_min
    skewness = np.sign(alpha_0 - (alpha_min + alpha_max) / 2)
    return {
        'alpha_min': alpha_min,
        'alpha_max': alpha_max,
        'alpha_0': alpha_0,
        'f_alpha_0': f_alpha_0,
        'delta_alpha': delta_alpha,
        'skewness': skewness,
        'alpha': alpha,
        'f_alpha': f_alpha
    }

if __name__ == "__main__":
    import sys
    default_csv = "nasdaq_100_historical_data_full.csv"
    path = sys.argv[1] if len(sys.argv) > 1 else default_csv

    print(f"# MF-DFA / Structure functions multifractal analysis")
    print(f"# Data: NASDAQ100, daily log returns, file: {path}")
    print("# Frequency: daily; Range: see file header")

    df = load_and_price(path, sample_step=1)

    print("\n## Data Diagnostics")
    print("First 5 rows:")
    print(df.head())
    print("\nWeekly Return stats:")
    print(df['WeeklyReturn'].describe())
    print("Number of NaN weekly returns:", df['WeeklyReturn'].isna().sum())
    returns = df['WeeklyReturn'].values
    print("Loaded weekly returns sample (first 10):", returns[:10])
    print("Total records loaded:", len(returns))

    q_list = [-5, -3, -2, 0, 2, 3, 5]
    tau_max = 20

    Sq = compute_structure_functions(returns, q_list, tau_max)
    tau_q = estimate_scaling_exponents(Sq, q_list)
    spectrum = fit_multifractal_spectrum(tau_q, q_list)

    print("\n## Multifractal Parameters")
    print(f"Hurst exponent (single): τ(2)/2 = {tau_q[2]/2:.4f}")
    print(f"Scaling exponents τ(q):")
    for q in q_list:
        print(f"  τ({q}): {tau_q[q]:.4f}")

    print("\n## Singularity Spectrum")
    print(f"α_min: {spectrum['alpha_min']:.4f}")
    print(f"α_max: {spectrum['alpha_max']:.4f}")
    print(f"α_0 mode: {spectrum['alpha_0']:.4f}")
    print(f"f(α_0): {spectrum['f_alpha_0']:.4f}")
    print(f"Spectrum width Δα: {spectrum['delta_alpha']:.4f}")
    print(f"Spectrum skewness: {'right' if spectrum['skewness']>0 else 'left' if spectrum['skewness']<0 else 'symmetric'}")

    print("\n## Goal/Question: Is the empirical return series multifractal (broad spectrum, skew), do parameters match literature, and is volatility clustering present or weak?")
