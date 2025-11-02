import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

def merge_data():
    """
    Loads processed S5P and CPCB data, harmonizes location names,
    merges the datasets, and saves the final master file.
    """
    print("--- Starting Data Merge Process ---")

    # --- 1. Define Paths ---
    try:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    except NameError:
        project_root = Path.cwd()
        print("Warning: Running interactively. Assuming current directory is project root.")

    s5p_path = project_root / 'data' / 'processed' / 'S5P_NRTI_Filled.csv'
    cpcb_path = project_root / 'data' / 'processed' / 'CPCB_Ground_Daily_Filled.csv'
    output_path = project_root / 'data' / 'processed' / 'master_aqi_merged_data.csv'

    # --- 2. Load CPCB Ground Data ---
    print(f"Loading CPCB data from: {cpcb_path}")
    try:
        cpcb_df = pd.read_csv(cpcb_path, parse_dates=['date'])
    except FileNotFoundError:
        print(f"ERROR: CPCB file not found at {cpcb_path}. Run CPCB preprocessing first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading CPCB data: {e}")
        sys.exit(1)

    # --- 3. Harmonize CPCB Location Names (CRUCIAL STEP) ---
    print("Harmonizing CPCB location names...")
    
    # This map is based on the screenshots you provided
    location_map = {
        'Anand Vihar, Delhi - DPCC': 'Anand Vihar, Delhi',
        'Mandir Marg Delhi - DPCC': 'Mandir Marg, Delhi',
        'Punjabi Bagh Delhi - DPCC': 'Punjabi Bagh, Delhi',
        'R K Puram Delhi - DPCC': 'RK Puram, Delhi',
        'Sector - 125 Noida - UPPCB': 'Sector 125, Noida',
        'Sector-51 Gurugram - HSPCB': 'Sector 51, Gurugram',
        'Vikas Sadan Gurugram - HSPCB': 'Vikas Sadan, Gurugram',
        
        # --- Add the 'Sector 62' variant here ---
        # Check your CPCB_Ground_Daily_Filled.csv for the exact name.
        # It's probably one of these (uncomment the correct one):
        # 'Sector - 62 Noida - UPPCB': 'Sector 62, Noida',
        # 'Sector-62, Noida - UPPCB': 'Sector 62, Noida',
        # 'Sector 62, Noida - UPPCB': 'Sector 62, Noida',
    }

    # Clean junk rows (e.g., if the header 'Location' was included as a row)
    cpcb_df = cpcb_df[cpcb_df['location'].str.strip() != 'Location'].copy()

    # Apply the mapping
    cpcb_df['location'] = cpcb_df['location'].str.strip().map(location_map).fillna(cpcb_df['location'])

    print("--- Post-Harmonization CPCB Locations ---")
    print(sorted(cpcb_df['location'].unique()))


    # --- 4. Load S5P Satellite Data ---
    print(f"Loading Satellite data from: {s5p_path}")
    try:
        s5p_df = pd.read_csv(s5p_path, parse_dates=['date'])
    except FileNotFoundError:
        print(f"ERROR: Satellite file not found at {s5p_path}. Run S5P preprocessing first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading satellite data: {e}")
        sys.exit(1)

    # --- 5. Rename Satellite Columns ---
    print("Renaming satellite columns...")
    s5p_rename_dict = {
        'NO2': 'NO2_satellite', 'SO2': 'SO2_satellite',
        'CO': 'CO_satellite', 'O3': 'O3_satellite',
        'Aerosol_Index': 'Aerosol_Index_satellite'
    }
    cols_to_rename = {k: v for k, v in s5p_rename_dict.items() if k in s5p_df.columns}
    s5p_df.rename(columns=cols_to_rename, inplace=True)
    print(f"Renamed S5P columns: {s5p_df.columns.tolist()}")

    # --- 6. Merge Data ---
    print("Merging S5P and CPCB data...")
    master_df = pd.merge(
        s5p_df,
        cpcb_df,
        on=['date', 'location'], # The keys to match
        how='outer'              # Keeps all rows from both files
    )
    master_df.sort_values(by=['location', 'date'], inplace=True)
    master_df.reset_index(drop=True, inplace=True)
    print("Merge complete.")

    # --- 7. Save Master DataFrame ---
    print(f"Saving master dataset to: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        master_df.to_csv(output_path, index=False)
        print(f"\n Master dataset saved successfully. Shape: {master_df.shape}")
        print("\n--- Master Data Head ---")
        print(master_df.head())
        
        print("\n--- Check for Missing Ground Data (Post-Merge) ---")
        # This will show if any S5P locations failed to match
        print(master_df[master_df['location'].isin(s5p_df['location'].unique())]['PM2.5_ground'].isnull().mean() * 100, "% of merged rows are missing ground data")
        
    except Exception as e:
        print(f"\nERROR: Failed to save master dataset. {e}")

# This makes the script runnable from the command line
if __name__ == "__main__":
    merge_data()