import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

print("--- Starting CPCB Data Preprocessing ---")

# --- Configuration ---
try:
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    raw_cpcb_path = project_root / 'data' / 'raw' / 'COMBINED_GROUND_DATA.csv' 
    processed_cpcb_path = project_root / 'data' / 'processed' / 'CPCB_Ground_Daily_Filled.csv'
except NameError:
    project_root = Path.cwd()
    raw_cpcb_path = project_root / 'data' / 'raw' / 'COMBINED_GROUND_DATA.csv'
    processed_cpcb_path = project_root / 'data' / 'processed' / 'CPCB_Ground_Daily_Filled.csv'
    print("Warning: Running interactively. Assuming current directory is project root.")

# *** UPDATED: Skip the 'Column1,Column2...' row ***
rows_to_skip = 1 

column_mapping = {
    'From Date': 'Datetime', 'PM2.5': 'PM2.5_ground', 'PM10': 'PM10_ground',
    'NO2': 'NO2_ground', 'SO2': 'SO2_ground', 'CO': 'CO_ground',
    'Ozone': 'O3_ground', 'Location': 'location'
}
datetime_column = 'Datetime'
date_format = '%d-%m-%Y %H:%M'
# --- End Configuration ---

final_pollutant_cols = [
    'PM2.5_ground', 'PM10_ground', 'NO2_ground',
    'SO2_ground', 'CO_ground', 'O3_ground'
]

# 1. Load Data
print(f"Loading raw CPCB data from: {raw_cpcb_path} (CSV file)")
if not raw_cpcb_path.is_file():
     print(f"ERROR: Raw CPCB file not found at '{raw_cpcb_path}'.")
     sys.exit(1)

try:
    # *** CORRECTED: header=0, skiprows=1 ***
    df = pd.read_csv(raw_cpcb_path, header=0, skiprows=rows_to_skip) 
    print(f"Raw data loaded successfully from CSV, skipping first {rows_to_skip} row(s). Shape: {df.shape}")
    if df.empty:
        print(f"ERROR: CSV file appears to be empty after skipping rows.")
        sys.exit(1)
    print(f"Columns read from CSV: {df.columns.tolist()}")

except Exception as e:
    print(f"ERROR: Failed to load raw CPCB data. {e}")
    sys.exit(1)

# 2. Initial Cleaning and Renaming
print("Renaming and selecting relevant columns...")
missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
if missing_cols:
    print(f"ERROR: The following required columns are missing from the CSV after skipping rows: {', '.join(missing_cols)}")
    print(f"Columns found in file: {df.columns.tolist()}")
    print("Please check the 'column_mapping' dictionary and the 'rows_to_skip' value.")
    sys.exit(1)

try:
    df = df[list(column_mapping.keys())]
    df.rename(columns=column_mapping, inplace=True)
except KeyError as e:
    print(f"ERROR: Column {e} not found during renaming.")
    sys.exit(1)

print(f"Columns after renaming: {df.columns.tolist()}")

# 3. Convert to Datetime
print(f"Converting '{datetime_column}' to datetime objects...")
try:
    if not pd.api.types.is_datetime64_any_dtype(df[datetime_column]):
        df[datetime_column] = pd.to_datetime(df[datetime_column], format=date_format, errors='coerce')
    original_len = len(df)
    df.dropna(subset=[datetime_column], inplace=True)
    if len(df) < original_len:
        print(f"Warning: Dropped {original_len - len(df)} rows due to invalid date/time format.")
except Exception as e:
    print(f"ERROR: Failed to convert datetime column. Check the 'date_format'. Error: {e}")
    sys.exit(1)

# 4. Convert Pollutants to Numeric
print("Converting pollutant columns to numeric...")
converted_pollutant_cols = []
for col in final_pollutant_cols:
    if col in df.columns:
        if df[col].dtype == 'object':
             df[col] = df[col].replace(['None', 'NA', 'N/A', '-'], np.nan, regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        converted_pollutant_cols.append(col)
    else:
        print(f"Warning: Expected column '{col}' not found. It will be missing.")

essential_cols = [datetime_column, 'location'] + converted_pollutant_cols
df = df[essential_cols]

# 5. Resample to Daily Averages
print("Resampling hourly data to daily averages for each location...")
if df.index.name != datetime_column:
    df.set_index(datetime_column, inplace=True)

try:
    numeric_resample_cols = df.select_dtypes(include=np.number).columns.intersection(converted_pollutant_cols)
    if not numeric_resample_cols.empty:
         daily_df = df.groupby('location')[list(numeric_resample_cols)].resample('D').mean()
    else:
         print("Warning: No numeric pollutant columns available for resampling.")
         daily_df = pd.DataFrame(index=df.groupby('location').resample('D').size().index)

    daily_df = daily_df.reset_index()
except Exception as e:
    print(f"ERROR: Failed during daily resampling. {e}")
    sys.exit(1)

if datetime_column in daily_df.columns:
     daily_df.rename(columns={datetime_column: 'date'}, inplace=True)
elif 'level_1' in daily_df.columns and pd.api.types.is_datetime64_any_dtype(daily_df['level_1']):
     daily_df.rename(columns={'level_1': 'date'}, inplace=True)

print(f"Resampling complete. Shape of daily data: {daily_df.shape}")
print("Sample of daily data:")
print(daily_df.head())

# 6. Handle Missing Daily Values (Interpolation)
print("Checking and filling missing values in daily data using linear interpolation...")
print("\nMissing values BEFORE interpolation (daily averages):")
print(daily_df.isnull().sum())

daily_filled_df = daily_df.copy()
interp_cols = daily_filled_df.select_dtypes(include=np.number).columns.intersection(converted_pollutant_cols)

if not interp_cols.empty:
    print(f"Interpolating columns: {', '.join(interp_cols)}")
    daily_filled_df[list(interp_cols)] = daily_filled_df.groupby('location')[list(interp_cols)].transform(
        lambda group: group.interpolate(method='linear', limit_direction='both', axis=0)
    )
    print("\nMissing values AFTER interpolation:")
    print(daily_filled_df.isnull().sum())
    if daily_filled_df[list(interp_cols)].isnull().any().any():
        print("\nWarning: Some NaNs remain after interpolation.")
else:
    print("No numeric pollutant columns found to interpolate in the daily data.")

# 7. Save Processed Data
print(f"Saving processed daily CPCB data to: {processed_cpcb_path}")
try:
    processed_cpcb_path.parent.mkdir(parents=True, exist_ok=True)
    daily_filled_df.to_csv(processed_cpcb_path, index=False)
    print("Processed daily CPCB data saved successfully.")
except Exception as e:
    print(f"ERROR: Failed to save processed data. {e}")
    sys.exit(1)

print("\n--- CPCB Data Preprocessing Finished ---")