# Phase 4: Data Preprocessing for AQI Discrepancy Prediction

## Overview

This document provides a comprehensive summary of the data preprocessing pipeline implemented for the Delhi-NCR AQI Assessment project. The preprocessing pipeline transforms the merged dataset (containing satellite data, ground measurements, and hyperlocal features) into a clean, feature-engineered dataset ready for machine learning model training.

## Input Dataset

**Source File:** `master_aqi_with_hyperlocal_features.csv`

The input dataset contains the following data sources merged together:
- **Satellite Data (Sentinel-5P NRTI):** NO2, SO2, CO, O3, and Aerosol Index measurements
- **Ground Measurements (CPCB):** PM2.5, PM10, NO2, SO2, CO, O3 from monitoring stations
- **Hyperlocal Context Features:** Road networks, land use, building characteristics extracted from OpenStreetMap

### Dataset Schema

The dataset includes the following columns:

**Satellite Features:**
- `NO2_satellite`: Nitrogen dioxide from satellite
- `SO2_satellite`: Sulfur dioxide from satellite
- `CO_satellite`: Carbon monoxide from satellite
- `O3_satellite`: Ozone from satellite
- `Aerosol_Index_satellite`: Aerosol index from satellite

**Ground Measurement Features:**
- `PM2.5_ground`: Particulate matter 2.5 (ground)
- `PM10_ground`: Particulate matter 10 (ground)
- `NO2_ground`: Nitrogen dioxide (ground)
- `SO2_ground`: Sulfur dioxide (ground)
- `CO_ground`: Carbon monoxide (ground)
- `O3_ground`: Ozone (ground)

**Location Metadata:**
- `location`: Monitoring station name
- `lat`: Latitude
- `lon`: Longitude
- `notes`: Source of location data
- `date`: Date of observation

**Hyperlocal Features:**
- `distance_to_major_road`: Distance to nearest major road (meters)
- `total_road_length_m`: Total road length in buffer (meters)
- `major_road_length_m`: Major road length in buffer (meters)
- `pct_green`: Percentage of green space
- `pct_industrial`: Percentage of industrial land use
- `pct_residential`: Percentage of residential land use
- `building_density`: Building density metric
- `avg_building_area_m2`: Average building area
- `median_building_area_m2`: Median building area
- `building_count`: Number of buildings in buffer
- `major_road_fraction`: Fraction of major roads

## Preprocessing Pipeline

### Step 1: Data Loading and Initial Setup

```python
import pandas as pd
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.max_columns', 100)

df = pd.read_csv("master_aqi_with_hyperlocal_features.csv")
```

**Actions:**
- Load the merged dataset into a pandas DataFrame
- Configure display options for better data inspection

### Step 2: Date Parsing and Validation

```python
df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
df = df.dropna(subset=['date'])
```

**Rationale:**
- The date column contains mixed formats (e.g., "01-01-2020", "2024-05-26")
- Using `dayfirst=True` handles DD-MM-YYYY format correctly
- `errors='coerce'` converts invalid dates to NaT (Not a Time) instead of raising errors

**Results:**
- Initial dataset: ~17,000+ rows
- After dropping invalid dates: **16,936 rows**
- All remaining rows have valid, parseable dates

### Step 3: Missing Value Analysis

Initial missing value counts identified:

**Satellite Data Missing Values:**
- `NO2_satellite`: 783 missing values
- `SO2_satellite`: 783 missing values
- `CO_satellite`: 783 missing values
- `O3_satellite`: 783 missing values
- `Aerosol_Index_satellite`: 783 missing values

**Hyperlocal Features Missing Values:**
- `pct_industrial`: 2,117 missing values
- `pct_residential`: 2,117 missing values
- `building_density`: 2,117 missing values
- `avg_building_area_m2`: 2,117 missing values
- `median_building_area_m2`: 2,117 missing values
- `building_count`: 2,117 missing values
- `major_road_fraction`: 2,117 missing values

**Complete Columns (No Missing Values):**
- All ground measurement columns (PM2.5, PM10, NO2, SO2, CO, O3)
- Location metadata (location, lat, lon, notes)
- Road-related hyperlocal features (distance_to_major_road, total_road_length_m, major_road_length_m)
- `pct_green`: 0 missing values

### Step 4: Missing Value Imputation

#### 4.1 Satellite Data Imputation: Backward Fill

```python
df = df.sort_values(by=['location', 'date'])
satellite_cols = ['NO2_satellite', 'SO2_satellite', 'CO_satellite', 
                  'O3_satellite', 'Aerosol_Index_satellite']
df[satellite_cols] = df.groupby('location')[satellite_cols].bfill()
```

**Strategy:** Backward fill (bfill) within each location group

**Rationale:**
- Satellite data is temporally continuous - missing values likely represent data gaps rather than true absence
- Backward fill propagates the next available value backward, which is appropriate for time-series satellite data
- Grouping by location ensures we only fill within the same monitoring station's time series
- Sorting by location and date ensures proper temporal ordering

**Results:**
- All 783 missing satellite values successfully imputed
- Final missing count: 0 for all satellite columns

#### 4.2 Hyperlocal Features Imputation: Mean Imputation

```python
hyperlocal_cols = [
    'pct_green',
    'pct_industrial',
    'pct_residential',
    'building_density',
    'avg_building_area_m2',
    'median_building_area_m2',
    'building_count',
    'major_road_fraction'
]

for col in hyperlocal_cols:
    mean_value = df[col].mean()
    df[col] = df[col].fillna(mean_value)
```

**Strategy:** Mean imputation

**Rationale:**
- Hyperlocal features are static or slowly-changing spatial characteristics
- Missing values likely indicate locations where feature extraction failed or wasn't available
- Mean imputation provides a reasonable default that preserves the overall distribution
- These features are less critical than satellite/ground measurements, so simple imputation is acceptable

**Imputed Mean Values:**
- `pct_green`: 0.077682 (7.77% green space on average)
- `pct_industrial`: 0.054804 (5.48% industrial land use)
- `pct_residential`: 0.488841 (48.88% residential land use)
- `building_density`: 0.142257
- `avg_building_area_m2`: 805.884142 m²
- `median_building_area_m2`: 416.861057 m²
- `building_count`: 1015.0 buildings
- `major_road_fraction`: 0.210922 (21.09% major roads)

**Results:**
- All 2,117 missing hyperlocal feature values successfully imputed
- Final missing count: 0 for all hyperlocal columns

### Step 5: Temporal Feature Engineering

```python
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek

def get_season(m):
    if m in [12,1,2]:
        return "Winter"
    elif m in [3,4]:
        return "Pre-Monsoon"
    elif m in [5,6,7,8,9]:
        return "Monsoon"
    else:
        return "Post-Monsoon"

df['season'] = df['month'].apply(get_season)
```

**Created Features:**

1. **`month`**: Integer (1-12) representing the month of the year
   - Captures seasonal patterns in air quality

2. **`day_of_week`**: Integer (0-6) where 0=Monday, 6=Sunday
   - Captures weekly patterns (weekday vs weekend effects)

3. **`season`**: Categorical feature with four seasons:
   - **Winter**: December, January, February
   - **Pre-Monsoon**: March, April
   - **Monsoon**: May, June, July, August, September
   - **Post-Monsoon**: October, November

**Rationale:**
- Air quality in Delhi-NCR exhibits strong seasonal patterns:
  - Winter: High pollution due to temperature inversions and stubble burning
  - Pre-Monsoon: Transition period with moderate pollution
  - Monsoon: Lower pollution due to rain and wind
  - Post-Monsoon: Increasing pollution as winter approaches
- Day of week captures weekly patterns (traffic, industrial activity)
- These temporal features help models learn time-dependent relationships

### Step 6: Target Variable Creation

```python
# Target variable: Option A (Ratio)
df['NO2_ratio'] = df['NO2_ground'] / df['NO2_satellite'].replace(0, pd.NA)
df['SO2_ratio'] = df['SO2_ground'] / df['SO2_satellite'].replace(0, pd.NA)
df['CO_ratio'] = df['CO_ground'] / df['CO_satellite'].replace(0, pd.NA)
df['O3_ratio'] = df['O3_ground'] / df['O3_satellite'].replace(0, pd.NA)

# Drop extreme/infinite values
df = df.replace([float('inf'), -float('inf')], pd.NA).dropna()
```

**Target Variables Created:**

1. **`NO2_ratio`**: `NO2_ground / NO2_satellite`
2. **`SO2_ratio`**: `SO2_ground / SO2_satellite`
3. **`CO_ratio`**: `CO_ground / CO_satellite`
4. **`O3_ratio`**: `O3_ground / O3_satellite`

**Rationale:**
- The ratio represents the **discrepancy** between ground measurements and satellite observations
- High ratios indicate ground measurements are much higher than satellite estimates
- Low ratios indicate ground measurements are lower than satellite estimates
- This ratio-based target variable allows models to learn the systematic differences between satellite and ground measurements
- The ratio captures both magnitude and direction of discrepancy

**Handling Edge Cases:**
- Zero satellite values are replaced with `pd.NA` to avoid division by zero
- Infinite values (resulting from very small satellite values) are converted to `pd.NA`
- Rows with any infinite or missing ratio values are dropped

**Data Quality:**
- The ratio values can be very large (e.g., 100,000+) when satellite values are extremely small
- This is expected behavior as satellite measurements are often much smaller in magnitude than ground measurements
- The model will learn to predict these ratios, which can then be used to correct satellite estimates

### Step 7: Data Cleaning and Final Validation

**Actions:**
- Removed rows with infinite ratio values
- Removed rows with missing ratio values (after division operations)
- Verified no remaining missing values in the dataset

**Final Dataset Characteristics:**
- All missing values imputed
- All temporal features created
- All target variables (ratios) computed
- No infinite or invalid values
- Ready for machine learning model training

### Step 8: Output Dataset

```python
output_path = "cleaned_aqi_merged_dataset.csv"
df.to_csv(output_path, index=False)
```

**Output File:** `cleaned_aqi_merged_dataset.csv`

**Final Dataset Schema:**

**Original Features (Preserved):**
- All satellite features (imputed)
- All ground measurement features
- All location metadata
- All hyperlocal features (imputed)

**New Features (Created):**
- `month`: Month of year (1-12)
- `day_of_week`: Day of week (0-6)
- `season`: Season category (Winter, Pre-Monsoon, Monsoon, Post-Monsoon)

**Target Variables (Created):**
- `NO2_ratio`: Ground-to-satellite ratio for NO2
- `SO2_ratio`: Ground-to-satellite ratio for SO2
- `CO_ratio`: Ground-to-satellite ratio for CO
- `O3_ratio`: Ground-to-satellite ratio for O3

## Summary Statistics

### Data Volume
- **Initial Rows:** ~17,000+ (before date validation)
- **After Date Validation:** 16,936 rows
- **After Ratio Calculation and Cleaning:** Final count depends on valid ratio computations

### Missing Value Resolution
- **Satellite Data:** 783 missing values → 0 (100% imputed via backward fill)
- **Hyperlocal Features:** 2,117 missing values → 0 (100% imputed via mean imputation)

### Feature Engineering
- **Temporal Features:** 3 new features (month, day_of_week, season)
- **Target Variables:** 4 new ratio features (NO2, SO2, CO, O3)

## Key Design Decisions

1. **Backward Fill for Satellite Data:**
   - Chosen because satellite data is temporally continuous
   - Preserves temporal relationships within each location

2. **Mean Imputation for Hyperlocal Features:**
   - Chosen because these are static spatial features
   - Simple and effective for missing spatial context data

3. **Ratio-Based Target Variables:**
   - Captures the discrepancy between ground and satellite measurements
   - Allows models to learn correction factors
   - More interpretable than absolute differences

4. **Seasonal Categorization:**
   - Based on Delhi-NCR's climate patterns
   - Aligns with known pollution patterns in the region

## Next Steps

The cleaned dataset (`cleaned_aqi_merged_dataset.csv`) is now ready for:
1. **Exploratory Data Analysis (EDA)**
2. **Feature Selection**
3. **Model Training** (predicting the ratio variables)
4. **Model Evaluation**

The preprocessing pipeline ensures data quality, handles missing values appropriately, and creates meaningful features and targets for machine learning model development.

