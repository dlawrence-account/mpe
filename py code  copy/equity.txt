# mpe/code/mpe/equity.py
def process_equity(df):
    """Compute basic equity stats."""
    return {
        "mean_return": float(df["LogReturns"].mean()),
        "volatility": float(df["LogReturns"].std())
    }
