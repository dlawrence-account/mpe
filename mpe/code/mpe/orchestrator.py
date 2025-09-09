# mpe/code/mpe/orchestrator.py
from . import io, validation, segmentation, maxent, equity, options_euro

def run_pipeline(csv_path, instrument, triple, k):
    df = io.load_csv(csv_path)
    triple = validation.validate_triple(triple)

    if "LogReturns" not in df.columns:
        raise KeyError("Input CSV must contain a 'LogReturns' column.")
    if "Date" not in df.columns:
        df["Date"] = range(len(df))

    segments = segmentation.segment_series(df["LogReturns"], k, dates=df["Date"])

    stats = equity.process_equity(df) if instrument == "equity" else options_euro.process_options(df)
    summary = maxent.analyze_regimes(segments, dates=df["Date"])

    return {"stats": stats, "maxent": summary}
