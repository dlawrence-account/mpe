# batch_once.py
import glob
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import time

# Import your analysis functions from triple_demo.py
from triple_demo import mfdfa_on_returns, volatility_measure_spectrum

def process_file(path):
    df = pd.read_csv(path, usecols=["date", "logreturns"])
    series = df["logreturns"].dropna().values
    res_r = mfdfa_on_returns(series)
    res_m = volatility_measure_spectrum(series)
    return {
        "ticker": Path(path).stem,
        "alpha0_returns": res_r["alpha0"],
        "H_returns": res_r["H"],
        "lambda_returns": res_r["lambda"],
        "alpha0_measure": res_m["alpha0"],
        "H_measure": res_m["H"],  # H-like slope for q=2
        "lambda_measure": res_m["lambda"]
    }

if __name__ == "__main__":
    files = glob.glob("mpe/*.csv")  # fixed to always look in mpe folder
    print(f"Found {len(files)} files to process")

    start_time = time.perf_counter()

    with ProcessPoolExecutor(max_workers=8) as ex:  # adjust cores if needed
        results = list(ex.map(process_file, files))

    elapsed = time.perf_counter() - start_time
    print(f"\nProcessed {len(files)} files in {elapsed:.2f} seconds")

    pd.DataFrame(results).to_csv("triples_batch.csv", index=False)
    print("Results saved to triples_batch.csv")
