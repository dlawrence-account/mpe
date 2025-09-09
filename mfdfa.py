import numpy as np
import pandas as pd
from scipy import stats, optimize
from scipy.stats import genpareto, levy_stable
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
    df = df.sort_values('Date').reset_index(drop=True)
    df['Price'] = 100 * np.exp(df['DailyLogReturns'].cumsum())
    df_s = df.iloc[::sample_step].copy().reset_index(drop=True)
    df_s['WeeklyReturn'] = np.log(df_s['Price']) - np.log(df_s['Price'].shift(1))
    return df_s.dropna(subset=['WeeklyReturn'])

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
    taus = np.arange(1, len(next(iter(Sq.values()))) + 1)
    log_taus = np.log(taus)
    tau_q = {}
    for q in q_list:
        slope, _, _, _, _ = stats.lin
