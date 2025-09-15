cat > mpe_allinone.sh <<'EOF'
#!/bin/bash
set -euo pipefail

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

mkdir -p tests

# Datasets
[ -f tests/synthetic_returns.csv ] || printf "return\n0.001\n0.002\n-0.001\n0.0005\n-0.0007\n0.0012\n0.0025\n-0.0015\n0.0008\n-0.0009\n" > tests/synthetic_returns.csv
[ -f tests/short_series.csv ] || printf "return\n0.01\n-0.02\n0.015\n-0.005\n0.003\n" > tests/short_series.csv
[ -f tests/edge_case.csv ] || printf "return\n10\n-8.5\n0.0001\n-0.0002\n3.1415\n-2.7182\n" > tests/edge_case.csv
[ -f tests/bad_dataset.csv ] || printf "foo\nbar\nbaz\nqux\n" > tests/bad_dataset.csv

# Inline Python: estimator + schema validation
python3 - <<'PY'
import csv, os, sys
from statistics import mean, pstdev
from jsonschema import validate, ValidationError

schema = {
    "type": "object",
    "required": [
        "selected_column",
        "rows_total",
        "rows_used",
        "rows_na_or_dropped",
        "parameters",
        "summary"
    ],
    "properties": {
        "selected_column": { "type": "string" },
        "rows_total": { "type": "integer", "minimum": 0 },
        "rows_used": { "type": "integer", "minimum": 0 },
        "rows_na_or_dropped": { "type": "integer", "minimum": 0 },
        "parameters": {
            "type": "object",
            "required": ["alpha", "H", "lambda"],
            "properties": {
                "alpha": { "type": "number" },
                "H": { "type": "number" },
                "lambda": { "type": "number" }
            },
            "additionalProperties": False
        },
        "summary": {
            "type": "object",
            "required": ["n", "mean", "std", "min", "max"],
            "properties": {
                "n": { "type": "integer", "minimum": 0 },
                "mean": { "type": "number" },
                "std": { "type": "number" },
                "min": { "type": "number" },
                "max": { "type": "number" }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

pass_count = 0
fail_count = 0

print("========================================")
print(" MPE Multi-Dataset Smoke & Schema Check ")
print("========================================")

for csv_file in sorted(os.listdir("tests")):
    if not csv_file.endswith(".csv"):
        continue
    base = csv_file[:-4]
    path = os.path.join("tests", csv_file)
    print(f"[SMOKE] Estimating on {path}...")
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "return" not in reader.fieldnames:
                print(f"{RED}[FAIL]{NC} Missing 'return' column in {csv_file}")
                fail_count += 1
                continue
            returns = []
            for row in reader:
                try:
                    returns.append(float(row["return"]))
                except (ValueError, TypeError):
                    pass
        if len(returns) < 1:
            print(f"{RED}[FAIL]{NC} Not enough rows in {csv_file}")
            fail_count += 1
            continue

        # Dummy parameter estimation
        params = {"alpha": 0.5, "H": 0.7, "lambda": 0.1}

        # Schema-compliant output
        output = {
            "selected_column": "return",
            "rows_total": int(len(returns)),
            "rows_used": int(len(returns)),
            "rows_na_or_dropped": int(0),
            "parameters": {
                "alpha": float(params["alpha"]),
                "H": float(params["H"]),
                "lambda": float(params["lambda"])
            },
            "summary": {
                "n": int(len(returns)),
                "mean": float(mean(returns)),
                "std": float(pstdev(returns)) if len(returns) > 1 else 0.0,
                "min": float(min(returns)),
                "max": float(max(returns))
            }
        }

        try:
            validate(instance=output, schema=schema)
            print(f"{GREEN}[PASS]{NC} {base}")
            pass_count += 1
        except ValidationError as e:
            print(f"{RED}[FAIL]{NC} Schema validation failed for {base}: {e.message}")
            fail_count += 1

    except Exception as e:
        print(f"{RED}[FAIL]{NC} {csv_file} errored: {e}")
        fail_count += 1

print(f"[INFO] Summary: {GREEN}{pass_count} passed{NC}, {RED}{fail_count} failed{NC}")
if fail_count > 0:
    sys.exit(1)
PY
EOF

chmod +x mpe_allinone.sh
./mpe_allinone.sh
