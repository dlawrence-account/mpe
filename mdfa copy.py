import numpy as np
import pandas as pd
from scipy import stats, optimize
from scipy.stats import genpareto, levy_stable

def load_and_price(csv_path, sample_step=5):
    """
    Load CSV with daily log returns, compute price series,
    sample every `sample_step` rows, and calculate weekly log returns.
    """
    df = pd.read_csv(csv_path, parse_dates=['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    # Reconstruct price from log returns
    df['Price'] = 100 * np.exp(df['DailyLogReturns'].cumsum())
    # Sample every sample_step rows
    df_s = df.iloc[::sample_step].copy().reset_index(drop=True)
    # Weekly log return on sampled series
    df_s['WeeklyReturn'] = np.log(df_s['Price']) - np.log(df_s['Price'].shift(1))
    return df_s.dropna(subset=['WeeklyReturn'])

def compute_Sq(returns, q_list, tau_max):
    """
    Compute structure functions S_q(tau) = E[|r(t+tau) - r(t)|^q]
    for tau = 1..tau_max and each q in q_list.
    """
    Sq = {q: [] for q in q_list}
    for tau in range(1, tau_max+1):
        diffs = np.abs(returns[tau:] - returns[:-tau])
        for q in q_list:
            Sq[q].append(np.mean(diffs**q))
    return {q: np.array(Sq[q]) for q in q_list}

def estimate_zeta_and_lambda(Sq, q_list):
    """
    1. For each q, regress log S_q vs log tau to get zeta(q).
    2. Fit zeta(q) = q*H - 0.5*lambda^2*(q^2 - q) to extract H and lambda.
    Returns H, lambda, and the zeta dictionary.
    """
    taus = np.arange(1, len(next(iter(Sq.values()))) + 1)
    log_taus = np.log(taus)
    zeta = {}
    for q in q_list:
        slope, _, _, _, _ = stats.linregress(log_taus, np.log(Sq[q]))
        zeta[q] = slope

    def model(q, H, lam):
        return q*H - 0.5*(lam**2)*(q**2 - q)

    popt, _ = optimize.curve_fit(
        model,
        np.array(q_list),
        np.array([zeta[q] for q in q_list])
    )
    H, lam = popt
    return H, lam, zeta

def fit_central_alpha(returns, central_pct=90):
    """
    Fit a symmetric Lévy–stable model to the central `central_pct`% of returns.
    Returns the estimated alpha.
    """
    low, high = np.percentile(returns, [(100-central_pct)/2, 100-(100-central_pct)/2])
    core = returns[(returns > low) & (returns < high)]
    alpha, _, _, _ = levy_stable.fit(core, floc=0, fbeta=0)
    return alpha

def estimate_far_tail_alpha(returns, tail_pct=1):
    """
    Estimate the far‐tail alpha using:
      - Hill estimator on the top `tail_pct`% of |returns|
      - POT (GPD) estimator on exceedances above the same threshold
    Returns (alpha_hill, alpha_pot).
    """
    abs_r = np.sort(np.abs(returns))
    k = max(int(len(abs_r) * tail_pct/100), 5)
    tail = abs_r[-k:]
    threshold = abs_r[-k-1]

    # Hill estimator
    alpha_hill = k / np.sum(np.log(tail / threshold))

    # POT/GPD estimator
    exceed = abs_r[abs_r > threshold] - threshold
    c, _, _ = genpareto.fit(exceed, floc=0)
    alpha_pot = 1/c if c > 0 else np.inf

    return alpha_hill, alpha_pot

if __name__ == "__main__":
    import sys
    # Updated filename
    default_csv = "Multifractals/nasdaq_100_historical_data_full.csv"
    path = sys.argv[1] if len(sys.argv) > 1 else default_csv

    df = load_and_price(path, sample_step=5)
    returns = df['WeeklyReturn'].values

    q_list = [-2, 0, 2, 3]
    tau_max = 20

    Sq = compute_Sq(returns, q_list, tau_max)
    H, lam, zeta = estimate_zeta_and_lambda(Sq, q_list)
    alpha = fit_central_alpha(returns)
    alpha_hill, alpha_pot = estimate_far_tail_alpha(returns)

    print(f"(alpha, alpha_ft, H, lambda)=({alpha:.4f}, {alpha_hill:.4f}, {H:.4f}, {lam:.4f})")
