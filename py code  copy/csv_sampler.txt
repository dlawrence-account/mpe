"""
csv_sampler.py

Utility for sampling and aggregating log returns from financial time series CSV files.
Creates different time-scale datasets for multifractal analysis.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

class LogReturnSampler:
    """
    Class for sampling and aggregating log returns at different time intervals.
    """
    
    def __init__(self, csv_file):
        """
        Initialize with a CSV file containing date and log return columns.
        """
        self.csv_file = csv_file
        self.df = None
        self.date_col = None
        self.return_col = None
        self._load_and_validate()
    
    def _load_and_validate(self):
        """
        Load and validate the CSV file, auto-detecting column names.
        """
        try:
            self.df = pd.read_csv(self.csv_file)
            print(f"✓ Loaded {len(self.df)} rows from {self.csv_file}")
            
            # Auto-detect date column
            for col in self.df.columns:
                if 'date' in col.lower():
                    self.date_col = col
                    break
            
            # Auto-detect return column  
            for col in self.df.columns:
                if 'return' in col.lower():
                    self.return_col = col
                    break
            
            if not self.date_col or not self.return_col:
                raise ValueError(f"Could not find date/return columns in {self.df.columns}")
            
            # Parse dates and sort
            self.df[self.date_col] = pd.to_datetime(self.df[self.date_col])
            self.df = self.df.sort_values(self.date_col).reset_index(drop=True)
            
            print(f"✓ Date column: '{self.date_col}' ({self.df[self.date_col].min().date()} to {self.df[self.date_col].max().date()})")
            print(f"✓ Return column: '{self.return_col}' (mean: {self.df[self.return_col].mean():.6f})")
            
        except Exception as e:
            print(f"✗ Failed to load/validate {self.csv_file}: {e}")
            raise
    
    def sample_at_interval(self, n_days, save_file=None):
        """
        Sample every n_days and aggregate log returns.
        
        Parameters:
        n_days: int - sampling interval in days
        save_file: str - optional filename to save results
        
        Returns:
        DataFrame with sampled dates and aggregated returns
        """
        sampled_data = []
        
        for i in range(0, len(self.df) - n_days + 1, n_days):
            end_idx = i + n_days - 1
            
            # Sum log returns over the interval (mathematically correct)
            aggregated_return = self.df.loc[i:end_idx, self.return_col].sum()
            
            sampled_data.append({
                'Date': self.df.loc[end_idx, self.date_col],
                'LogReturn': aggregated_return,
                'IntervalDays': n_days,
                'StartDate': self.df.loc[i, self.date_col]
            })
        
        result = pd.DataFrame(sampled_data)
        
        print(f"✓ Created {len(result)} observations at {n_days}-day intervals")
        print(f"✓ Aggregated stats - Mean: {result['LogReturn'].mean():.6f}, Std: {result['LogReturn'].std():.4f}")
        
        if save_file:
            result.to_csv(save_file, index=False)
            print(f"✓ Saved to: {save_file}")
        
        return result
    
    def create_multiple_samples(self, intervals=[5, 10, 22], output_prefix=None):
        """
        Create multiple sampled datasets at different intervals.
        
        Parameters:
        intervals: list of int - sampling intervals in days
        output_prefix: str - prefix for output filenames
        
        Returns:
        dict - {interval: DataFrame} mapping
        """
        if output_prefix is None:
            base_name = os.path.splitext(os.path.basename(self.csv_file))[0]
            output_prefix = f"{base_name}_sampled"
        
        results = {}
        
        for interval in intervals:
            print(f"\n--- Sampling at {interval}-day intervals ---")
            save_file = f"{output_prefix}_{interval}day.csv"
            results[interval] = self.sample_at_interval(interval, save_file)
        
        return results

# Standalone usage
if __name__ == "__main__":
    print("CSV Log Return Sampler")
    print("=" * 50)
    
    # Example usage
    sampler = LogReturnSampler("nasdaq100_returns.csv")
    
    # Create multiple samples
    samples = sampler.create_multiple_samples([5, 10, 22])
    
    print("\n" + "=" * 50)
    print("Sampling complete. Files created:")
    for interval in samples:
        print(f"  • nasdaq100_returns_sampled_{interval}day.csv ({len(samples[interval])} observations)")
