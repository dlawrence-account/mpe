cat << 'EOF' > scripts/select_csv.sh
#!/usr/bin/env bash
#
# Terminal pop-up selector for CSVs in tests/in, outputs cleaned CSV to tests/out.
# Suppresses warnings, limits preview to first 5 rows.
# Requires: dialog (install via brew install dialog)

CSV_DIR="$(cd "$(dirname "\$0")/../tests/in" && pwd)"
OUT_DIR="$(cd "$(dirname "\$0")/../tests/out" && pwd)"
mkdir -p "\$OUT_DIR"

MENU_ITEMS=()
for f in "\$CSV_DIR"/*.csv; do
  [ -f "\$f" ] || continue
  python3 - "\$f" <<PYCODE
import sys,pandas as pd
path=sys.argv[1]
df=pd.read_csv(path)
if not {'date','logreturns'}.issubset(df.columns): sys.exit(1)
if pd.to_datetime(df['date'], errors='coerce').isna().any(): sys.exit(1)
if pd.to_numeric(df['logreturns'], errors='coerce').isna().any(): sys.exit(1)
sys.exit(0)
PYCODE
  if [ \$? -eq 0 ]; then
    MENU_ITEMS+=(\"\$(basename \"\$f\")\" \"\")
  fi
done

if [ \${#MENU_ITEMS[@]} -eq 0 ]; then
  echo "No valid CSVs in \$CSV_DIR" >&2
  exit 1
fi

CHOICE=\$(dialog \
  --clear \
  --title "Select CSV" \
  --menu "Use ↑/↓ and Enter; Esc to cancel" \
  15 60 8 \
  \"\${MENU_ITEMS[@]}\" \
  3>&1 1>&2 2>&3
)

if [ \$? -ne 0 ]; then
  clear
  echo "Selection cancelled." >&2
  exit 1
fi

clear

python3 - <<PYCODE
import os,pandas as pd,warnings
warnings.filterwarnings("ignore", message="Could not infer format")
CSV_DIR = "\$CSV_DIR"
OUT_DIR = "\$OUT_DIR"
choice = "\$CHOICE"
input_path = os.path.join(CSV_DIR, choice)
output_path = os.path.join(OUT_DIR, choice.replace('.csv','_cleaned.csv'))
df = pd.read_csv(input_path)
df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['date'])
df['logreturns'] = pd.to_numeric(df['logreturns'], errors='coerce')
df = df.dropna(subset=['logreturns'])
df.to_csv(output_path, index=False)
print(f"Saved: {output_path} ({len(df)} rows)")
print("Preview (5 rows):")
print(df.head(5).to_string(index=False))
PYCODE
EOF
