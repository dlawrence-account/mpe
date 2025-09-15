print("TESTING IMPORTS")

try:
    import numpy as np
    print("✓ numpy imported successfully")
except ImportError as e:
    print(f"✗ numpy import failed: {e}")

try:
    import pandas as pd
    print("✓ pandas imported successfully")
except ImportError as e:
    print(f"✗ pandas import failed: {e}")

try:
    import matplotlib.pyplot as plt
    print("✓ matplotlib imported successfully")
except ImportError as e:
    print(f"✗ matplotlib import failed: {e}")

try:
    from scipy.stats import linregress
    print("✓ scipy imported successfully")
except ImportError as e:
    print(f"✗ scipy import failed: {e}")

print("IMPORT TEST COMPLETE")

