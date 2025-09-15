#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mpe_estimator.py

Driver script for multifractal parameter estimation.
- Reads a numeric series from CSV or STDIN
- Validates and cleans the data
- Calls estimate_parameters_from_series() from parameter_estimation.py
- Outputs results in text or JSON
"""

import argparse
import csv
import io
import json
import sys
from typing import List, Optional, Dict, Any

import numpy as np

from parameter_estimation import estimate_parameters_from_series

NUMERIC_SENTINELS = {"", "na", "n/a", "nan", "null", "none", "."}


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def _read_csv_series(
    fp: io.TextIOBase,
    wanted_column: Optional[str],
    na_policy: str,
    max_rows: Optional[int],
) -> (np.ndarray, Dict[str, Any]):
    reader = csv.reader(fp)
    rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty.")

    header = None
    start_idx = 0
    first_row = rows[0]
    if any((c.strip().lower() in NUMERIC_SENTINELS) or (not _is_float(c)) for c in first_row):
        header = [c.strip() for c in first_row]
        start_idx = 1

    data_rows = rows[start_idx:]
    if max_rows is not None:
        data_rows = data_rows[:max_rows]

    if header is not None and wanted_column is not None:
        if wanted_column not in header:
            raise ValueError(f"Requested column '{wanted_column}' not found in header: {header}")
        col_idx = header.index(wanted_column)
    elif header is not None and wanted_column is None:
        if "logreturns" in header:
            col_idx = header.index("logreturns")
        else:
            col_idx = 0
    else:
        col_idx = 0

    values: List[float] = []
    na_count = 0
    total_rows = 0

    for r in data_rows:
        total_rows += 1
        cell = r[col_idx].strip() if col_idx < len(r) else ""
        if cell.lower() in NUMERIC_SENTINELS:
            if na_policy == "drop":
                na_count += 1
                continue
            elif na_policy == "zero":
                values.append(0.0)
            else:
                raise ValueError(f"NA encountered at row {start_idx + total_rows}.")
        else:
            try:
                values.append(float(cell))
            except Exception:
                if na_policy == "drop":
                    na_count += 1
                    continue
                elif na_policy == "zero":
                    values.append(0.0)
                else:
                    raise ValueError(f"Non-numeric value '{cell}' at row {start_idx + total_rows}.")

    arr = np.asarray(values, dtype=float)
    diagnostics = {
        "header_present": header is not None,
        "selected_column": (header[col_idx] if header is not None else f"col_{col_idx}"),
        "rows_total": total_rows,
        "rows_used": int(arr.shape[0]),
        "rows_na_or_dropped": int(na_count),
    }
    return arr, diagnostics


def _validate_series(x: np.ndarray, min_len: int) -> None:
    if x.ndim != 1:
        raise ValueError(f"Series must be 1-D; got shape {x.shape}.")
    if x.size < min_len:
        raise ValueError(f"Series length {x.size} is below minimum required {min_len}.")
    if not np.all(np.isfinite(x)):
        raise ValueError("Series contains non-finite values after NA handling.")


def run_estimation(x: np.ndarray, seed: Optional[int] = None) -> Dict[str, float]:
    if seed is not None:
        np.random.seed(seed)
    params = estimate_parameters_from_series(x)
    if not isinstance(params, dict):
        raise RuntimeError("Estimator did not return a dict of parameters.")
    return {str(k): float(v) for k, v in params.items()}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="mpe_estimator.py",
        description="Estimate multifractal parameters from a CSV series.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", "-i", required=True, help="Path to CSV file or '-' for STDIN.")
    p.add_argument("--column", "-c", default=None, help="Column name to use.")
    p.add_argument("--na-policy", choices=["drop", "fail", "zero"], default="drop")
    p.add_argument("--min-len", type=int, default=128)
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--out", default=None)
    p.add_argument("--summary", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    try:
        if args.input == "-":
            text_stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
        else:
            text_stream = open(args.input, "r", encoding="utf-8", errors="replace")
    except Exception as e:
        sys.stderr.write(f"InputError: cannot open input '{args.input}': {e}\n")
        # "params": params,

    try:
        with text_stream:
            series, diag = _read_csv_series(
                fp=text_stream,
                wanted_column=args.column,
                na_policy=args.na_policy,
                max_rows=args.max_rows,
            )
    except Exception as e:
        sys.stderr.write(f"SchemaError: {e}\n")
        return 4

    try:
        _validate_series(series, min_len=args.min_len)
    except Exception as e:
        sys.stderr.write(f"ValidationError: {e}\n")
        return 4

    summary = None
    if args.summary:
        summary = {
            "n": int(series.size),
            "mean": float(np.mean(series)),
            "std": float(np.std(series, ddof=1)) if series.size > 1 else float("nan"),
            "min": float(np.min(series)),
            "max": float(np.max(series)),
        }

    try:
        params = run_estimation(series, seed=args.seed)
    except Exception as e:
        sys.stderr.write(f"EstimationError: {e}\n")
        return 5

    payload = {
        "selected_column": diag["selected_column"],
        "rows_total": diag["rows_total"],
        "rows_used": diag["rows_used"],
        "rows_na_or_dropped": diag["rows_na_or_dropped"],
        "parameters": params,
    }
    if summary is not None:
        payload["summary"] = summary

    try:
        if args.format == "json":
            out_str = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            lines: List[str] = []
            lines.append(f"Column: {payload['selected_column']}")
            lines.append(
                f"Rows: total={payload['rows_total']}, "
                f"used={payload['rows_used']}, "
                f"na_or_dropped={payload['rows_na_or_dropped']}"
            )
            if summary is not None:
                s = payload["summary"]
                lines.append(
                    f"Summary: n={s['n']}, mean={s['mean']:.6g}, "
                    f"std={s['std']:.6g}, min={s['min']:.6g}, max={s['max']:.6g}"
                )
            for k, v in payload["parameters"].items():
                lines.append(f"{k}: {v:.6g}")
            out_str = "\n".join(lines)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_str + "\n")
        else:
            sys.stdout.write(out_str + "\n")
    except Exception as e:
        sys.stderr.write(f"OutputError: {e}\n")
        return 6

    return 0


if __name__ == "__main__":
    sys.exit(main())
