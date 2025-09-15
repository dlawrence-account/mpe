#!/bin/bash
# ci_synthetic_test.sh
# Non-interactive synthetic test harness for CI

set -euo pipefail

echo "=== CI Synthetic Test ==="

# Create and activate venv if not already present
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies (adjust if you have a requirements.txt)
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    pip install pandas numpy
fi

# Step 1: Generate synthetic data
python multifractals/make_synthetic.py

# Step 2: Run MPE pipeline
python -m mpe.code.mpe.main \
  --csv multifractals/data/synthetic_test.csv \
  --instrument equity \
  --triple 0.5 0.2 1.0 \
  --k 3

# Step 3: Verify boundaries
VERIFY_OUTPUT=$(python multifractals/verify_boundaries.py)
echo "$VERIFY_OUTPUT"

# Pass/fail check
if echo "$VERIFY_OUTPUT" | grep -q "✅ All boundaries within"; then
    echo "🎯 CI Synthetic test PASSED"
else
    echo "❌ CI Synthetic test FAILED"
    exit 1
fi
