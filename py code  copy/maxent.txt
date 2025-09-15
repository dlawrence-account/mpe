#!/usr/bin/env python
"""
MaxEnt segmentation interface (stub).
Replace the heuristic with your real MaxEnt implementation.
"""

from typing import Dict, List
import numpy as np

def run_maxent(series: np.ndarray, k: int) -> Dict[str, List[int]]:
    n = int(len(series))
    if k <= 1 or n <= 1:
        return {"boundaries": []}

    returns = np.diff(series, prepend=series[0])
    energy = np.abs(returns)

    cuts = np.linspace(0, n - 1, num=k, endpoint=False)[1:].round().astype(int).tolist()
    cuts = sorted(set(max(0, min(n - 2, c)) for c in cuts))

    window = 3
    refined = []
    for c in cuts:
        lo = max(1, c - window)
        hi = min(n - 2, c + window)
        local = np.argmax(energy[lo:hi + 1]) + lo
        refined.append(int(local))
    refined = sorted(set(refined))

    return {"boundaries": refined}
