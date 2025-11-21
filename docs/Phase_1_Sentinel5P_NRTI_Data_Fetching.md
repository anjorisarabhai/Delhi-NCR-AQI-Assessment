# Phase 1: Sentinel-5P NRTI Data Fetching from Google Earth Engine

## Overview

Phase 1 of the Delhi-NCR AQI Assessment project focuses on extracting daily time-series data for multiple air quality pollutants from Sentinel-5P satellite observations using Google Earth Engine (GEE). This process retrieves Near Real-Time (NRTI) Level 3 products for five key atmospheric constituents across eight monitoring locations in the Delhi-NCR region, covering the period from 2020 to the present.

## Purpose

The satellite data extraction process aims to:

- **Extract multi-pollutant time series**: Retrieve daily measurements for NO₂, SO₂, CO, O₃, and Aerosol Index
- **Cover multiple locations**: Process data for 8 key monitoring stations across Delhi, Gurugram, and Noida
- **Enable temporal analysis**: Provide continuous daily data from 2020 to present for trend analysis
- **Support AQI modeling**: Supply satellite-derived pollutant concentrations as features for air quality assessment
- **Handle interruptions gracefully**: Resume data extraction from the last processed point if the script is interrupted

## Dependencies

The following Python packages are required:

```python
earthengine-api  # Google Earth Engine Python API
pandas           # Data manipulation and CSV handling
```

Install with:
```bash
pip install earthengine-api pandas
```

### Google Earth Engine Authentication

Before running the script, you must authenticate with Google Earth Engine:

```bash
earthengine authenticate
```

This will open a browser window for authentication. After authentication, you can initialize the API with your project ID.

## Setup and Configuration

### Google Earth Engine Initialization

The script initializes Google Earth Engine with a specific project ID:

```python
ee.Initialize(project='enhanced-bonito-457316-v6')
```

**Key Requirements:**
- Valid Google Earth Engine account with authentication
- Project ID must match your GEE project
- Active internet connection for API calls

### Study Area: Monitoring Locations

The script processes data for 8 locations across Delhi-NCR:

1. **Anand Vihar, Delhi** - 28.6473°N, 77.3185°E
2. **RK Puram, Delhi** - 28.5643°N, 77.1818°E
3. **Punjabi Bagh, Delhi** - 28.6678°N, 77.1213°E
4. **Mandir Marg, Delhi** - 28.6274°N, 77.2010°E
5. **Vikas Sadan, Gurugram** - 28.4601°N, 77.0318°E
6. **Sector 51, Gurugram** - 28.4287°N, 77.0706°E
7. **Sector 62, Noida** - 28.6195°N, 77.3618°E
8. **Sector 125, Noida** - 28.5376°N, 77.3338°E

### Temporal Coverage

- **Start Year**: 2020
- **End Year**: Current year (automatically determined)
- **Granularity**: Daily data aggregated by month
- **Update Frequency**: Script processes up to the current date

## Sentinel-5P Products

The script extracts data from five Sentinel-5P NRTI (Near Real-Time) Level 3 collections:

### 1. Nitrogen Dioxide (NO₂)
- **Collection**: `COPERNICUS/S5P/NRTI/L3_NO2`
- **Band**: `tropospheric_NO2_column_number_density`
- **Units**: mol/m²
- **Description**: Tropospheric NO₂ column number density, a key indicator of urban air pollution and traffic emissions

### 2. Sulfur Dioxide (SO₂)
- **Collection**: `COPERNICUS/S5P/NRTI/L3_SO2`
- **Band**: `SO2_column_number_density`
- **Units**: mol/m²
- **Description**: Total SO₂ column number density, primarily from industrial sources and power plants

### 3. Carbon Monoxide (CO)
- **Collection**: `COPERNICUS/S5P/NRTI/L3_CO`
- **Band**: `CO_column_number_density`
- **Units**: mol/m²
- **Description**: Total CO column number density, indicator of incomplete combustion from vehicles and industry

### 4. Ozone (O₃)
- **Collection**: `COPERNICUS/S5P/NRTI/L3_O3`
- **Band**: `O3_column_number_density`
- **Units**: mol/m²
- **Description**: Total O₃ column number density, important for understanding photochemical smog formation

### 5. Aerosol Index
- **Collection**: `COPERNICUS/S5P/NRTI/L3_AER_AI`
- **Band**: `absorbing_aerosol_index`
- **Units**: Dimensionless
- **Description**: Absorbing aerosol index, indicates presence of absorbing aerosols (dust, smoke, pollution)

**Note**: NRTI (Near Real-Time) products are available within hours of satellite overpass, making them suitable for recent data analysis. For historical analysis, consider using OFFL (Offline) products which have undergone more complete processing.

## Core Functions

### `get_s5p_time_series(product_info, point, start_date, end_date)`

Extracts a time series for a specific pollutant at a point location using Google Earth Engine's efficient `getRegion` method.

**Process:**
1. **Select collection and band**: Filters the appropriate Sentinel-5P collection and selects the target band
2. **Filter by date range**: Applies temporal filter for the specified month
3. **Extract time series**: Uses `getRegion()` to efficiently extract point values across all images in the collection
4. **Parse results**: Converts GEE response (list of lists) into structured data
5. **Format dates**: Converts millisecond timestamps to YYYY-MM-DD format
6. **Error handling**: Implements retry logic for transient GEE API errors

**Parameters:**
- `product_info`: Dictionary containing `collection` and `band` keys
- `point`: Earth Engine Point geometry (longitude, latitude)
- `start_date`: Start date string in 'YYYY-MM-DD' format
- `end_date`: End date string in 'YYYY-MM-DD' format

**Returns:**
- List of dictionaries with `date` and `value` keys
- Empty list if no data found or on persistent errors

**Error Handling:**
- Automatic retry once on `EEException` with 5-second delay
- Skips corrupted rows gracefully
- Returns empty list if retry also fails

**Technical Details:**
- Uses `scale=1000` (1km resolution) for point extraction
- Handles masked/missing values (returns `None` in value field)
- Efficient for time-series extraction compared to per-image processing

## Processing Pipeline

### Main Execution Loop

The script processes data in a nested loop structure:

```
For each location:
    For each year (2020 to present):
        For each month (1 to 12, or current month):
            For each pollutant (NO2, SO2, CO, O3, Aerosol_Index):
                1. Extract time series for the month
                2. Merge with other pollutants by date
                3. Add location identifier
                4. Append to output CSV
```

**Processing Order:**
1. Locations are processed sequentially
2. Years are processed chronologically
3. Months are processed from January to December (or current month)
4. Pollutants are processed sequentially with 0.5-second delays between API calls

### Resume Functionality

The script includes robust resume capability to handle interruptions:

**Resume Detection:**
1. Checks if output file exists and has content (>50 bytes)
2. Reads the last entry from the CSV
3. Identifies the last processed location, year, and month
4. Skips already-completed locations entirely
5. Resumes from the next month for the partially-completed location

**Resume Logic:**
- Completed locations are tracked and skipped
- Partial months are re-processed (data is appended, duplicates removed later)
- If file is corrupted, script attempts to delete and start fresh

**Output File:**
- Path: `data/raw/S5P_AQI_Data_Delhi_NCR_2020_Present_NRTI.csv`
- Format: CSV with columns: `date`, `NO2`, `SO2`, `CO`, `O3`, `Aerosol_Index`, `location`
- Mode: Append mode for incremental updates

### Rate Limiting

The script implements rate limiting to avoid overwhelming the GEE API:
- **0.5 seconds** delay between pollutant API calls
- **5 seconds** delay before retry attempts
- Sequential processing prevents concurrent API overload

### Data Merging

For each location-month combination:
1. Individual pollutant DataFrames are created from time series
2. DataFrames are merged on `date` using outer join (preserves all dates)
3. Duplicate dates are removed (keeps first occurrence)
4. Location name is added as a column
5. Columns are reordered to match header specification
6. Data is appended to CSV file

## Output

### Output File Structure

**File Path**: `data/raw/S5P_AQI_Data_Delhi_NCR_2020_Present_NRTI.csv`

**Columns:**
- `date`: Date in YYYY-MM-DD format
- `NO2`: Tropospheric NO₂ column number density (mol/m²)
- `SO2`: SO₂ column number density (mol/m²)
- `CO`: CO column number density (mol/m²)
- `O3`: O₃ column number density (mol/m²)
- `Aerosol_Index`: Absorbing aerosol index (dimensionless)
- `location`: Location name (e.g., "Anand Vihar, Delhi")

**Data Characteristics:**
- **Temporal Resolution**: Daily
- **Spatial Resolution**: 1km (point extraction)
- **Missing Values**: Represented as `None` or `NaN` in CSV
- **Date Coverage**: May have gaps due to cloud cover, satellite overpass timing, or data availability

### Data Quality Considerations

**Strengths:**
- Global coverage with consistent methodology
- Near real-time availability (NRTI products)
- Multiple pollutants from single satellite platform
- Long temporal coverage (2020-present)

**Limitations:**
- **Cloud cover**: Satellite observations may be missing on cloudy days
- **Overpass timing**: Sentinel-5P has specific overpass times, may not capture diurnal variations
- **Spatial resolution**: 1km resolution may not capture hyperlocal variations
- **Data gaps**: Some dates may have missing values for specific pollutants
- **Quality flags**: Script does not filter by quality flags (all available data is extracted)

## Usage

### Basic Execution

```bash
python scripts/get_satellite_data.py
```

### Prerequisites

1. **Authenticate with Google Earth Engine:**
   ```bash
   earthengine authenticate
   ```

2. **Ensure output directory exists:**
   ```bash
   mkdir -p data/raw
   ```

3. **Update project ID** (if needed):
   Edit line 10 in the script to use your GEE project ID:
   ```python
   ee.Initialize(project='your-project-id')
   ```

### Running the Script

The script will:
1. Initialize Google Earth Engine
2. Check for existing output file and resume if found
3. Process each location sequentially
4. Print progress messages for each location, year, and month
5. Save data incrementally to CSV
6. Complete when all locations and time periods are processed

### Expected Runtime

- **Per location-month**: ~2-5 seconds (5 pollutants × 0.5s delay + API calls)
- **Per location (full period)**: ~30-60 minutes (depending on data availability)
- **Total (8 locations, 2020-present)**: ~4-8 hours

**Note**: Runtime depends on:
- Internet connection speed
- GEE API response times
- Amount of data available for each time period
- Number of retries needed

### Monitoring Progress

The script provides progress output:
```
Starting data extraction...

Processing Location: Anand Vihar, Delhi
  -- Processing 2020-01
    -- Successfully saved data for 2020-01
  -- Processing 2020-02
    -- Successfully saved data for 2020-02
...
```

If resuming:
```
Found existing data file: data/raw/S5P_AQI_Data_Delhi_NCR_2020_Present_NRTI.csv. Reading last entry to resume.
Resuming after Anand Vihar, Delhi for 2020-05

Skipping Location: RK Puram, Delhi (already complete).
```

## Error Handling

### Network Errors

- **Initialization failure**: Script exits with error message
- **API errors during extraction**: Automatic retry with 5-second delay
- **Persistent errors**: Skips the current chunk and continues

### Data Errors

- **Corrupted CSV**: Script attempts to delete and start fresh
- **Missing data**: Returns empty list, script continues
- **Invalid timestamps**: Skipped with exception handling

### Recovery

If the script is interrupted:
1. Simply re-run the script
2. It will automatically detect the last processed point
3. Resume from the next unprocessed month
4. Skip already-completed locations

## Technical Considerations

### Google Earth Engine API

- **Quota limits**: GEE has usage quotas; very large requests may be throttled
- **Authentication**: Requires valid Google account with Earth Engine access
- **Project ID**: Must match an active GEE project
- **API version**: Uses the Python client library (earthengine-api)

### Data Processing

- **Memory efficiency**: Processes one month at a time, appends to CSV
- **Disk space**: CSV file grows incrementally; ensure sufficient storage
- **Date handling**: Uses Python's `datetime` and `calendar` modules for accurate date calculations

### Coordinate System

- **Input**: Longitude, Latitude in decimal degrees (WGS84)
- **GEE processing**: Uses native GEE coordinate system
- **Output**: Dates and values only (no explicit coordinate storage)

## Next Steps

The extracted satellite data can be used for:

1. **Temporal Analysis**: Analyze trends and seasonality in pollutant concentrations
2. **Spatial Comparison**: Compare pollutant levels across different locations
3. **Data Integration**: Merge with ground-based monitoring data (CPCB stations)
4. **Feature Engineering**: Create derived features (rolling averages, anomalies, etc.)
5. **Modeling**: Use as predictor variables in AQI prediction models
6. **Visualization**: Create time series plots and maps

## References

- [Google Earth Engine Documentation](https://developers.google.com/earth-engine)
- [Sentinel-5P Mission](https://sentinel.esa.int/web/sentinel/missions/sentinel-5p)
- [Sentinel-5P Data Products](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-5p-tropomi)
- [Earth Engine Python API](https://github.com/google/earthengine-api)
- [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/)


