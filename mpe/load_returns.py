import os
import numpy as np

def load_returns_from_csv():
    """
    Prompts the user for a CSV file path in the console.
    Returns a 1D numpy array of returns, or None on error/cancel.
    """
    path = input("Enter path to returns CSV file (leave blank to cancel): ").strip()
    if not path:
        print("Loading cancelled.")
        return None

    if not os.path.isfile(path):
        print(f"Error: File does not exist: {path}")
        return None
    if not os.access(path, os.R_OK):
        print(f"Error: Cannot read file: {path}")
        return None

    try:
        data = np.loadtxt(path, delimiter=",", skiprows=1)
    except ValueError:
        print("Error: Expected a single column of numeric returns.")
        return None
    except Exception as e:
        print(f"Unexpected error loading file: {e}")
        return None

    if data.ndim != 1:
        print("Error: Expected one column of returns, got multiple.")
        return None

    return data

if __name__ == "__main__":
    returns = load_returns_from_csv()
    if returns is None:
        print("No valid returns data loaded; exiting.")
    else:
        from mpe_estimator import MAPMEstimator
        estimator = MAPMEstimator(returns)
        params = estimator.estimate_parameters()
        print("Estimated parameters:", params)
