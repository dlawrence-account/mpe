#!/bin/bash
# run_test.sh
# Unified harness for synthetic or real-data MPE+MaxEnt testing with schema validation
# Usage:
#   ./run_test.sh                # synthetic mode (default)
#   ./run_test.sh synthetic      # explicit synthetic mode
#   ./run_test.sh real           # real mode, latest CSV in data/input/
#   ./run_test.sh real --file nasdaq100_returns.csv
#   ./run_test.sh real --file=nasdaq100_returns.csv

set -euo pipefail

MODE="${1:-synthetic}"  # default to synthetic if no arg given
ARG2="${2:-}"           # could be --file or --file=filename or empty
ARG3="${3:-}"           # filename if using --file <filename>

# Activate venv
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
else
    echo "❌ Could not find ../venv/bin/activate — is your virtual environment created?"
    exit 1
fi

# Ensure folder structure exists
mkdir -p data/input
mkdir -p data/output

EXPECTED="date,logreturns"

if [ "$MODE" = "synthetic" ]; then
    echo
    echo "=== Step 1: Generating synthetic test data ==="
    python make_synthetic.py || { echo "❌ Synthetic data generation failed"; exit 1; }

    SYNTH_CSV="data/synthetic_test.csv"
    if [ ! -f "$SYNTH_CSV" ]; then
        echo "❌ Synthetic CSV not found after generation"
        exit 1
    fi

    HEADER=$(head -n 1 "$SYNTH_CSV" | tr -d '\r\n')
    if [ "$HEADER" != "$EXPECTED" ]; then
        echo "❌ Schema mismatch in synthetic CSV"
        echo "   Expected: $EXPECTED"
        echo "   Found:    $HEADER"
        exit 1
    fi

    mv -f "$SYNTH_CSV" data/input/

else
    echo
    echo "=== Real-data mode: Skipping synthetic generation ==="

    TARGET_FILE=""
    if [[ "$ARG2" == "--file" ]]; then
        if [ -z "$ARG3" ]; then
            echo "❌ No filename provided after --file"
            exit 1
        fi
        TARGET_FILE="data/input/$ARG3"
    elif [[ "$ARG2" == --file=* ]]; then
        TARGET_FILE="data/input/${ARG2#--file=}"
    elif [ -z "$ARG2" ]; then
        TARGET_FILE=$(ls -t data/input/*.csv 2>/dev/null | head -n 1 || true)
    else
        echo "❌ Unknown argument: $ARG2"
        exit 1
    fi

    if [ -z "$TARGET_FILE" ] || [ ! -f "$TARGET_FILE" ]; then
        echo "❌ CSV not found: $TARGET_FILE"
        exit 1
    fi

    HEADER=$(head -n 1 "$TARGET_FILE" | tr -d '\r\n')
    if [ "$HEADER" != "$EXPECTED" ]; then
        echo "❌ Schema mismatch in real-data CSV"
        echo "   Expected: $EXPECTED"
        echo "   Found:    $HEADER"
        exit 1
    fi

    # Touch file so main.py picks it up as "latest"
    touch "$TARGET_FILE"
fi

echo
echo "=== Step 2: Running MPE pipeline ==="
python -m mpe.code.mpe.main \
  --instrument equity \
  --triple 0.5 0.2 1.0 \
  --k 3 || { echo "❌ MPE pipeline failed"; exit 1; }

echo
echo "=== Step 3: Verification ==="
python verify_boundaries.py
