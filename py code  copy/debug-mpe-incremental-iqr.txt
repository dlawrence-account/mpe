print("TESTING MPE WITH SAMPLED DATA (IQR INSTEAD OF STD)")

import pandas as pd
import numpy as np
from mapm_parameters import estimate_alpha, estimate_hurst, estimate_lambda

def interquartile_range(x):
    """Return the IQR of array x."""
    q75, q25 = np.percentile(x, [75 ,25])
    return q75 - q25

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

test_files = [
    "nasdaq100_returns_sampled_22day.csv",
    "nasdaq100_returns_sampled_10day.csv",
    "nasdaq100_returns_sampled_5day.csv"
]

for test_file in test_files:
    success = test_mpe_on_sample(test_file)
    if not success:
        print(f"✗ Stopping at {test_file} due to failure")
        break

print("\nMPE INCREMENTAL TEST COMPLETE")
