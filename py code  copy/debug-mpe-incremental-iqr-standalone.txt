print("TESTING MPE WITH SAMPLED DATA (IQR INSTEAD OF STD)")

import pandas as pd
import numpy as np
from scipy.stats import linregress

def interquartile_range(x):
    """Return the IQR of array x."""
    q75, q25 = np.percentile(x, [75, 25])
    return q75 - q25

def estimate_alpha(returns, tail_fraction=0.05):
    """Estimate alpha via Hill estimator."""
    r = np.sort(np.abs(returns))
    n = len(r)
    k = max(2, int(np.floor(n * tail_fraction)))
    tail = r[-k:]
    logs = np.log(tail)
    alpha = 1.0 / np.mean(logs - logs[0])
    return alpha

def estimate_hurst(returns, lags=None):
    """Estimate Hurst exponent H."""
    if lags is None:
        lags = np.arange(2, min(41, len(returns)//4))
    rs = []
    for lag in lags:
        if len(returns) > lag:
            diffs = returns[lag:] - returns[:-lag]
            rs.append(np.mean(np.abs(diffs)))
    if len(rs) > 1:
        slope, _, _, _, _ = linregress(np.log(lags[:len(rs)]), np.log(rs))
        return slope
    return 0.5

def estimate_lambda(returns, lags=None):
    """Estimate lambda via covariance decay."""
    if lags is None:
        lags = np.arange(2, min(41, len(returns)//4))
    logabs = np.log(np.abs(returns) + 1e-12)
    covs = []
    for lag in lags:
        if len(logabs) > lag:
            covs.append(np.cov(logabs[lag:], logabs[:-lag])[0,1])
    if len(covs) > 1:
        slope, _, _, _, _ = linregress(np.log(lags[:len(covs)]), covs)
        return np.sqrt(max(0.0, -slope))
    return 0.1

def test_mpe_on_sample(csv_file):
    """Test MPE parameter estimation on a sampled dataset using IQR."""
    
    print(f"\n--- Testing MPE on {csv_file} ---")
    try:
        df = pd.read_csv(csv_file)
        returns = df['LogReturn'].values
        
        iqr = interquartile_range(returns)
        print(f"✓ Loaded {len(returns)} observations")
        print(f"✓ Return IQR: {iqr:.6f}")
        
        alpha = estimate_alpha(returns)
        H = estimate_hurst(returns)
        lambda_param = estimate_lambda(returns)
        
        print(f"✓ Alpha (scaling): {alpha:.4f}")
        print(f"✓ Hurst H (memory): {H:.4f}")
        print(f"✓ Lambda (clustering): {lambda_param:.4f}")
        
        return True
        
    except Exception as e:
        print(f"✗ MPE test failed: {e}")
        return False

# Test files in order of increasing size
test_files = [
    "nasdaq100_returns_sampled_22day.csv",  # 227 obs
    "nasdaq100_returns_sampled_10day.csv",  # 499 obs  
    "nasdaq100_returns_sampled_5day.csv"    # 999 obs
]

for test_file in test_files:
    success = test_mpe_on_sample(test_file)
    if not success:
        print(f"✗ Stopping at {test_file} due to failure")
        break

print("\nMPE INCREMENTAL TEST COMPLETE")
