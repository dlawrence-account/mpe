#!/usr/bin/env bash
#
# mpe/scripts/select_csv.sh
# Terminal pop-up selector for CSVs in tests/in, outputs cleaned CSV to tests/out.
# Bulletproof with error handling and reporting.
# Requires: dialog (install via brew install dialog), python3, pandas

set -euo pipefail

# Dependency checks
command -v dialog >/dev/null 2>&1 || { echo "Error: 'dialog' not found. Install with: brew install dialog"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: 'python3' not found"; exit 1; }
python3 -c "import pandas" 2>/dev/null || { echo "Error: pandas not available. Install with: pip3 install pandas"; exit 1; }

# Paths
BASEDIR="$(cd "$(dirname "$0")/.." && pwd)"
CSV_DIR="$BASEDIR/tests/in"
OUT_DIR="$BASEDIR/tests/out"

# Validate input directory
[[ -d "$CSV_DIR" ]] || { echo "Error: Input directory not found: $CSV_DIR"; exit 1; }
# Create output directory
mkdir -p "$OUT_DIR"

echo "Scanning CSVs in $CSV_DIR..." >&2

# Build menu items
MENU_ITEMS=()
for f in "$CSV_DIR"/*.csv; do
  [[ -f "$f" ]] || continue
  if python3 - "$f" <<PYCODE
import sys, pandas as pd
path = sys.argv[1]
df = pd.read_csv(path)
if not {'date','logreturns'}.issubset(df.columns): sys.exit(1)
if pd.to_datetime(df['date'], errors='coerce').isna().any(): sys.exit(1)
if pd.to_numeric(df['logreturns'], errors='coerce').isna().any(): sys.exit(1)
sys.exit(0)
PYCODE
  then
    MENU_ITEMS+=("$(basename "$f")" "$(wc -l <"$f" | tr -d ' ') rows")
  fi
done

[[ ${#MENU_ITEMS[@]} -gt 0 ]] || { echo "No valid CSVs found."; exit 1; }

CHOICE=$(dialog --clear --title "Select CSV" --menu "Choose a file:" 15 50 8 "${MENU_ITEMS[@]}" 3>&1 1>&2 2>&3)
[[ $? -eq 0 ]] || { clear; echo "Cancelled"; exit 1; }
clear

python3 - <<PYCODE
import os, pandas as pd, warnings
warnings.filterwarnings("ignore", message="Could not infer format")
csvdir = "$CSV_DIR"
outdir = "$OUT_DIR"
choice = "$CHOICE"
inp = os.path.join(csvdir, choice)
outp = os.path.join(outdir, choice.replace('.csv','_cleaned.csv'))
df = pd.read_csv(inp)
df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['date'])
df['logreturns'] = pd.to_numeric(df['logreturns'], errors='coerce')
df = df.dropna(subset=['logreturns'])
df.to_csv(outp, index=False)
print(f"Saved: {outp} ({len(df)} rows)")
print(df.head(5).to_string(index=False))
PYCODE
