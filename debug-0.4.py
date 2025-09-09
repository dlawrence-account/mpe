print("TESTING BASIC MAPM FUNCTIONS")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress

print("✓ All imports successful")

# Test basic parameter estimation functions
def estimate_alpha(returns, tail_fraction=0.05):
    r = np.sort(np.abs(returns))
    n = len(r)
    k = max(2, int(np.floor(n * tail_fraction)))
    tail = r[-k:]
    logs = np.log(tail)
    alpha = 1.0 / np.mean(logs - logs[0])
    return alpha

# Generate test data
np.random.seed(42)
test_returns = np.random.normal(0, 0.01, 1000)

try:
    alpha = estimate_alpha(test_returns)
    print(f"✓ Alpha estimation successful: {alpha:.4f}")
except Exception as e:
    print(f"✗ Alpha estimation failed: {e}")

print("BASIC FUNCTIONS TEST COMPLETE")
