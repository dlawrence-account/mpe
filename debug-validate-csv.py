print("VALIDATING nasdaq100_returns.csv")

import pandas as pd
import numpy as np
import os

def validate_csv_file(filename):
    """
    Validate CSV file without making assumptions about structure or date range.
    """
    try:
        # Check if file exists
        if not os.path.exists(filename):
            print(f"✗ File not found: {filename}")
            return None
            
        print(f"✓ File found: {filename}")
        print(f"✓ File size: {os.path.getsize(filename)} bytes")
        
        # Load and inspect
        df = pd.read_csv(filename)
        print(f"✓ Loaded successfully")
        print(f"✓ Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Show column names
        print(f"✓ Columns: {list(df.columns)}")
        
        # Show first few rows
        print("\n✓ First 3 rows:")
        print(df.head(3))
        
        # Show data types
        print(f"\n✓ Data types:")
        print(df.dtypes)
        
        # Try to parse dates (flexible approach)
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col:
            try:
                df[date_col] = pd.to_datetime(df[date_col])
                print(f"✓ Date column '{date_col}' parsed successfully")
                print(f"✓ Date range: {df[date_col].min()} to {df[date_col].max()}")
                print(f"✓ Total days: {(df[date_col].max() - df[date_col].min()).days}")
            except Exception as e:
                print(f"✗ Date parsing failed: {e}")
        
        # Look for return column
        return_col = None
        for col in df.columns:
            if 'return' in col.lower():
                return_col = col
                break
                
        if return_col:
            returns = df[return_col].dropna()
            print(f"✓ Return column '{return_col}' found")
            print(f"✓ Return stats - Count: {len(returns)}, Mean: {returns.mean():.6f}, Std: {returns.std():.4f}")
            print(f"✓ Return range: {returns.min():.6f} to {returns.max():.6f}")
        
        return df
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return None

# Validate the file
df = validate_csv_file("nasdaq100_returns.csv")

if df is not None:
    print(f"\n✓ CSV validation successful - ready for sampling")
else:
    print(f"\n✗ CSV validation failed")

print("\nCSV VALIDATION COMPLETE")
