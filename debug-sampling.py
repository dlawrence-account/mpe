print("TESTING LOG RETURN SAMPLING SCRIPT")

import pandas as pd
import numpy as np

def sample_and_aggregate_returns(csv_file, n_days):
    """
    Sample every n records and sum the log returns between samples.
    """
    try:
        # Load data
        df = pd.read_csv(csv_file, parse_dates=['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"✓ Loaded {len(df)} daily observations")
        print(f"✓ Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Sample every n_days and aggregate returns
        sampled_data = []
        
        for i in range(0, len(df) - n_days + 1, n_days):
            end_idx = i + n_days - 1
            
            # Sum log returns over the interval
            aggregated_return = df.loc[i:end_idx, 'return'].sum()
            
            sampled_data.append({
                'date': df.loc[end_idx, 'date'],  # End date of interval
                'return': aggregated_return,
                'interval_days': n_days
            })
        
        result = pd.DataFrame(sampled_data)
        print(f"✓ Created {len(result)} observations at {n_days}-day intervals")
        print(f"✓ Return stats - Mean: {result['return'].mean():.6f}, Std: {result['return'].std():.4f}")
        
        return result
        
    except Exception as e:
        print(f"✗ Sampling failed: {e}")
        return None

# Test the sampling function
if __name__ == "__main__":
    print("Testing with nasdaq100returns.csv...")
    
    # Test different sampling intervals
    for n_days in [5, 10]:  # Weekly, bi-weekly
        print(f"\n--- Testing {n_days}-day sampling ---")
        sampled = sample_and_aggregate_returns("nasdaq100returns.csv", n_days)
        
        if sampled is not None:
            output_file = f"nasdaq100_sampled_{n_days}day.csv"
            sampled.to_csv(output_file, index=False)
            print(f"✓ Saved: {output_file}")
        else:
            print(f"✗ Failed to create {n_days}-day sample")
            break

print("\nSAMPLING TEST COMPLETE")
