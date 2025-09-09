import ruptures as rpt
import numpy as np

def segment_series(series, k, dates=None, min_size=10):
    """
    Segment a time series into k regimes using statistical change-point detection.

    Parameters
    ----------
    series : array-like
        The numeric series to segment (e.g., log returns).
    k : int
        Desired number of regimes.
    dates : array-like or None
        Optional labels for the series (e.g., dates).
    min_size : int
        Minimum number of observations per regime.

    Returns
    -------
    list of tuple
        Consecutive (start_label, end_label) tuples.
    """
    arr = np.asarray(series)

    # Primary method: Binary Segmentation with RBF cost
    try:
        algo = rpt.Binseg(model="rbf", min_size=min_size).fit(arr)
        bkps = algo.predict(n_bkps=k)
    except Exception:
        # Fallback: PELT with RBF cost
        algo = rpt.Pelt(model="rbf", min_size=min_size).fit(arr)
        bkps = algo.predict(pen=3)  # penalty can be tuned

    # Convert breakpoints to (start, end) labels
    segments = []
    start_idx = 0
    for bkp in bkps:
        end_idx = bkp - 1
        start_label = dates[start_idx] if dates is not None else start_idx
        end_label = dates[end_idx] if dates is not None else end_idx
        segments.append((start_label, end_label))
        start_idx = bkp

    return segments
