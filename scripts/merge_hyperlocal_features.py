import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

def merge_hyperlocal_features():
    """
    Loads hyperlocal context features and master AQI merged data,
    merges them on station names, and saves the result.
    """
    print("--- Starting Hyperlocal Features Merge Process ---")

    # --- 1. Define Paths ---
    try:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    except NameError:
        project_root = Path.cwd()
        print("Warning: Running interactively. Assuming current directory is project root.")

    hyperlocal_path = project_root / 'data' / 'raw' / 'delhi_hyperlocal_context_features_1000m.csv'
    master_aqi_path = project_root / 'data' / 'processed' / 'master_aqi_merged_data.csv'
    output_path = project_root / 'data' / 'processed' / 'master_aqi_with_hyperlocal_features.csv'

    # --- 2. Load Hyperlocal Features Data ---
    print(f"Loading hyperlocal features from: {hyperlocal_path}")
    try:
        hyperlocal_df = pd.read_csv(hyperlocal_path)
    except FileNotFoundError:
        print(f"ERROR: Hyperlocal features file not found at {hyperlocal_path}.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading hyperlocal features: {e}")
        sys.exit(1)

    print(f"Hyperlocal features shape: {hyperlocal_df.shape}")
    print("--- Hyperlocal Station Names ---")
    print(sorted(hyperlocal_df['station'].unique()))

    # --- 3. Load Master AQI Data ---
    print(f"\nLoading master AQI data from: {master_aqi_path}")
    try:
        master_df = pd.read_csv(master_aqi_path, parse_dates=['date'])
    except FileNotFoundError:
        print(f"ERROR: Master AQI file not found at {master_aqi_path}. Run merge_datasets.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading master AQI data: {e}")
        sys.exit(1)

    print(f"Master AQI data shape: {master_df.shape}")
    print("--- Master AQI Location Names ---")
    print(sorted(master_df['location'].unique()))

    # --- 4. Harmonize Station Names (if needed) ---
    print("\nChecking for station name mismatches...")
    
    # Create a mapping for any name differences
    # Based on the existing merge script pattern, we might need to handle variations
    station_map = {
        # Add any name mappings here if needed
        # Format: 'name_in_hyperlocal': 'name_in_master'
    }
    
    # Apply mapping if any exists
    if station_map:
        hyperlocal_df['station'] = hyperlocal_df['station'].map(station_map).fillna(hyperlocal_df['station'])
        print("Applied station name mappings.")
    
    # Check for mismatches
    hyperlocal_stations = set(hyperlocal_df['station'].unique())
    master_locations = set(master_df['location'].unique())
    
    common_stations = hyperlocal_stations.intersection(master_locations)
    only_hyperlocal = hyperlocal_stations - master_locations
    only_master = master_locations - hyperlocal_stations
    
    print(f"\nCommon stations: {len(common_stations)}")
    if common_stations:
        print(sorted(common_stations))
    
    if only_hyperlocal:
        print(f"\nStations only in hyperlocal data ({len(only_hyperlocal)}):")
        print(sorted(only_hyperlocal))
    
    if only_master:
        print(f"\nLocations only in master AQI data ({len(only_master)}):")
        print(sorted(only_master))

    # --- 5. Merge Data ---
    print("\nMerging hyperlocal features with master AQI data...")
    merged_df = pd.merge(
        master_df,
        hyperlocal_df,
        left_on='location',
        right_on='station',
        how='left'  # Keep all rows from master AQI data
    )
    
    # Drop the duplicate 'station' column if it exists (since we merged on it)
    if 'station' in merged_df.columns and 'location' in merged_df.columns:
        # Keep 'location' as the primary identifier
        merged_df = merged_df.drop(columns=['station'])
    
    merged_df.sort_values(by=['location', 'date'], inplace=True)
    merged_df.reset_index(drop=True, inplace=True)
    print("Merge complete.")

    # --- 6. Save Merged DataFrame ---
    print(f"\nSaving merged dataset to: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged_df.to_csv(output_path, index=False)
        print(f"✓ Merged dataset saved successfully. Shape: {merged_df.shape}")
        
        print("\n--- Merged Data Head ---")
        print(merged_df.head())
        
        print("\n--- Summary Statistics ---")
        print(f"Total rows: {len(merged_df)}")
        print(f"Total columns: {len(merged_df.columns)}")
        
        # Check how many rows have hyperlocal features
        hyperlocal_cols = [col for col in merged_df.columns if col not in master_df.columns]
        if hyperlocal_cols:
            print(f"\nHyperlocal feature columns added: {len(hyperlocal_cols)}")
            print(f"Columns: {', '.join(hyperlocal_cols)}")
            
            # Count rows with hyperlocal data
            rows_with_features = merged_df[hyperlocal_cols[0]].notna().sum()
            print(f"Rows with hyperlocal features: {rows_with_features} ({rows_with_features/len(merged_df)*100:.2f}%)")
        
    except Exception as e:
        print(f"\nERROR: Failed to save merged dataset. {e}")
        sys.exit(1)

# This makes the script runnable from the command line
if __name__ == "__main__":
    merge_hyperlocal_features()

