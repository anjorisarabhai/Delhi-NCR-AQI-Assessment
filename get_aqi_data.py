import ee
import pandas as pd
import time
from datetime import datetime
from calendar import monthrange
import os

# Initialize with your specific project ID.
try:
    ee.Initialize(project='enhanced-bonito-457316-v6')
    print('Google Earth Engine Initialized Successfully.')
except Exception as e:
    print(f"Could not initialize Earth Engine: {e}")
    print("This is likely a network issue. Check your internet connection and try again.")
    exit()

# 1. DEFINE YOUR STUDY AREA AND PARAMETERS
locations = {
    'Anand Vihar, Delhi': (77.3185, 28.6473),
    'RK Puram, Delhi': (77.1818, 28.5643),
    'Punjabi Bagh, Delhi': (77.1213, 28.6678),
    'Mandir Marg, Delhi': (77.2010, 28.6274),
    'Vikas Sadan, Gurugram': (77.0318, 28.4601),
    'Sector 51, Gurugram': (77.0706, 28.4287),
    'Sector 62, Noida': (77.3618, 28.6195),
    'Sector 125, Noida': (77.3338, 28.5376)
}

start_year = 2020
current_time = datetime.now()
end_year = current_time.year
years_to_process = range(start_year, end_year + 1)

# Using NRTI (Near Real-Time) collections
s5p_products = {
    'NO2': {'collection': 'COPERNICUS/S5P/NRTI/L3_NO2', 'band': 'tropospheric_NO2_column_number_density'},
    'SO2': {'collection': 'COPERNICUS/S5P/NRTI/L3_SO2', 'band': 'SO2_column_number_density'},
    'CO': {'collection': 'COPERNICUS/S5P/NRTI/L3_CO', 'band': 'CO_column_number_density'},
    'O3': {'collection': 'COPERNICUS/S5P/NRTI/L3_O3', 'band': 'O3_column_number_density'},
    'Aerosol_Index': {'collection': 'COPERNICUS/S5P/NRTI/L3_AER_AI', 'band': 'absorbing_aerosol_index'}
}
product_names = list(s5p_products.keys())

# 2. --- MODIFIED FUNCTION: Using getRegion for efficient time-series extraction ---
def get_s5p_time_series(product_info, point, start_date, end_date):
    """Extracts a time series using the efficient getRegion method."""
    band = product_info['band']
    collection = ee.ImageCollection(product_info['collection'])\
                   .select(band)\
                   .filterDate(start_date, end_date)
    
    try:
        # getRegion is the most efficient way to get a time-series for a point.
        time_series = collection.getRegion(geometry=point, scale=1000).getInfo()
        
        if not time_series or len(time_series) < 2:
            return [] # No data found

        # Parse the result (it's a list of lists)
        header = time_series[0]
        data_rows = time_series[1:]

        # Find the column indices for 'time' and the band value
        try:
            date_index = header.index('time')
            value_index = header.index(band)
        except ValueError as e:
            print(f"    -- Error parsing GEE results: {e}. Header was: {header}")
            return []

        data = []
        for row in data_rows:
            try:
                # 'time' is a timestamp in milliseconds, convert it to YYYY-MM-DD
                timestamp_ms = row[date_index]
                if timestamp_ms is None:
                    continue # Skip rows with no time
                
                date_str = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d')
                value = row[value_index] # This will be 'None' if data is masked
                data.append({'date': date_str, 'value': value})
            except Exception:
                continue # Skip corrupted rows
                
        return data

    except ee.EEException as e:
        print(f"    -- GEE Error during fetch. Retrying once... Details: {e}")
        time.sleep(5) 
        try:
            # Retry the exact same request
            time_series = collection.getRegion(geometry=point, scale=1000).getInfo()
            
            if not time_series or len(time_series) < 2:
                return []

            header = time_series[0]
            data_rows = time_series[1:]
            
            date_index = header.index('time')
            value_index = header.index(band)

            data = []
            for row in data_rows:
                try:
                    timestamp_ms = row[date_index]
                    if timestamp_ms is None:
                        continue
                    date_str = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d')
                    value = row[value_index]
                    data.append({'date': date_str, 'value': value})
                except Exception:
                    continue
            return data
            
        except ee.EEException as e_retry:
            print(f"    -- GEE Error on retry. Skipping this chunk. Details: {e_retry}")
            return []
            
# 3. SETUP FOR RESUMING SCRIPT
output_filename = 'S5P_AQI_Data_Delhi_NCR_2020_Present_NRTI.csv' # Using NRTI file
resume_point = None
processed_locations = []
file_exists = os.path.exists(output_filename)
header_cols = ['date'] + product_names + ['location']

if file_exists and os.path.getsize(output_filename) > 50: 
    print(f"Found existing data file: {output_filename}. Reading last entry to resume.")
    try:
        df_existing = pd.read_csv(output_filename)
        if not df_existing.empty:
            last_entry = df_existing.iloc[-1]
            last_date = pd.to_datetime(last_entry['date'])
            resume_point = {
                'location': last_entry['location'],
                'year': last_date.year,
                'month': last_date.month
            }
            processed_locations = df_existing[df_existing['location'] != resume_point['location']]['location'].unique().tolist()
            print(f"Resuming after {resume_point['location']} for {resume_point['year']}-{resume_point['month']:02d}")
    except Exception as e:
        print(f"Could not read existing file, starting from scratch. Error: {e}")
        try:
            os.remove(output_filename) 
        except OSError as oe:
            print(f"Error deleting file {output_filename}. Please delete it manually. {oe}")
            exit()
        file_exists = False

if not file_exists:
    print(f"No valid data found. Creating new file: {output_filename}")
    pd.DataFrame(columns=header_cols).to_csv(output_filename, index=False)

# 4. MAIN PROCESSING LOOP
print("Starting data extraction...")
for loc_name, coords in locations.items():
    
    if loc_name in processed_locations:
        print(f"\nSkipping Location: {loc_name} (already complete).")
        continue

    print(f"\nProcessing Location: {loc_name}")
    point_geometry = ee.Geometry.Point(coords)

    for year in years_to_process:
        last_month = 12 if year < current_time.year else current_time.month
        
        for month in range(1, last_month + 1):
            
            if resume_point and loc_name == resume_point['location']:
                if year < resume_point['year'] or (year == resume_point['year'] and month <= resume_point['month']):
                    continue 

            start_date = f'{year}-{month:02d}-01'
            last_day_of_month = monthrange(year, month)[1]
            end_date = f'{year}-{month:02d}-{last_day_of_month}'
            
            if year == current_time.year and month == current_time.month:
                end_date = current_time.strftime('%Y-%m-%d')
            
            print(f"  -- Processing {year}-{month:02d}")
            
            location_one_month_df = pd.DataFrame()
            for gas, product_info in s5p_products.items():
                time.sleep(0.5) 
                ts_data = get_s5p_time_series(product_info, point_geometry, start_date, end_date)
                
                if ts_data:
                    temp_df = pd.DataFrame(ts_data).rename(columns={'value': gas})
                    if location_one_month_df.empty:
                        location_one_month_df = temp_df
                    else:
                        location_one_month_df = pd.merge(location_one_month_df, temp_df, on='date', how='outer')
            
            if not location_one_month_df.empty:
                location_one_month_df = location_one_month_df.drop_duplicates(subset=['date'])
                location_one_month_df['location'] = loc_name
                location_one_month_df = location_one_month_df.reindex(columns=header_cols)
                
                location_one_month_df.to_csv(output_filename, mode='a', header=False, index=False)
                print(f"    -- Successfully saved data for {year}-{month:02d}")

print(f"\n Data extraction complete! All data saved to {output_filename}")