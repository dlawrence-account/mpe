# mpe/code/mpe/io.py
import pandas as pd
from pathlib import Path

def load_csv(path):
    """Load a CSV file into a pandas DataFrame."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(p)
