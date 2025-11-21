# Phase 4: PM2.5 Discrepancy Prediction Model Building

## Overview

This document describes the machine learning pipeline developed to predict the discrepancy between ground-based and satellite-derived PM2.5 measurements in the Delhi-NCR region. The goal is to build a model that can estimate the difference between actual ground measurements and satellite proxy values, enabling better calibration and correction of satellite data.

## Problem Statement

Satellite data does not provide direct PM2.5 measurements. Instead, we have:
- **Ground data**: Direct PM2.5 measurements from monitoring stations
- **Satellite data**: Aerosol Index (AI) and other atmospheric parameters (NO2, SO2, CO, O3)

The challenge is to predict the discrepancy between ground PM2.5 and satellite-derived estimates using Aerosol Index as a proxy.

## Target Variable

The target variable is defined as:

```
target_diff = PM2.5_ground - (Aerosol_Index_satellite * scaling_factor)
```

Where:
- `PM2.5_ground`: Direct ground measurements (ground-exclusive metric)
- `Aerosol_Index_satellite`: Satellite proxy for PM2.5 (ranges typically -2 to 2)
- `scaling_factor`: Conversion factor (default: 50.0) to approximate PM2.5 from Aerosol Index

**Note**: PM2.5 and PM10 are ground-exclusive metrics. Satellite data only provides:
- NO2_satellite
- SO2_satellite
- CO_satellite
- O3_satellite
- Aerosol_Index_satellite (used as proxy for PM2.5)

## Dataset

### Data Source
- **File**: `cleaned_aqi_merged_dataset.csv`
- **Location**: `notebooks/model-training/`
- **Shape**: 16,936 rows × 34 columns (after target creation: 35 columns)

### Features

**Total Features**: 30 (expands to 38 after preprocessing with one-hot encoding)

#### Satellite Features (5)
- NO2_satellite
- SO2_satellite
- CO_satellite
- O3_satellite
- Aerosol_Index_satellite (used as proxy for satellite PM2.5)

#### Ground Features (5)
- PM10_ground
- NO2_ground
- SO2_ground
- CO_ground
- O3_ground

#### Location Features (2)
- lat (latitude)
- lon (longitude)

#### Hyperlocal Context Features (12)
- distance_to_major_road
- total_road_length_m
- major_road_length_m
- pct_green
- pct_industrial
- pct_residential
- building_density
- avg_building_area_m2
- median_building_area_m2
- building_count
- major_road_fraction

#### Temporal Features (3)
- month (1-12)
- day_of_week (0-6)
- season (Winter, Spring, Summer, Monsoon, Autumn)

#### Ratio Features (4)
- NO2_ratio (ground/satellite)
- SO2_ratio (ground/satellite)
- CO_ratio (ground/satellite)
- O3_ratio (ground/satellite)

#### Categorical Features (2)
- location (monitoring station location)
- season

## Data Preprocessing

### 1. Target Variable Creation
- Identified `PM2.5_ground` column
- Used `Aerosol_Index_satellite` as proxy for satellite PM2.5
- Applied scaling factor of 50.0 to convert Aerosol Index to approximate PM2.5
- Calculated discrepancy: `target_diff = PM2.5_ground - (Aerosol_Index_satellite * 50.0)`

### 2. Data Cleaning
- Filtered unrealistic values:
  - PM2.5_ground: -10 to 1000 μg/m³
  - Removed rows with missing target values
- **Result**: No rows removed (all values within acceptable range)

### 3. Feature Engineering
- **Excluded columns**: `date`, `target_diff`, `PM2.5_ground`, `Aerosol_Index_satellite`, `notes`
- **Categorical encoding**: One-hot encoding for `location` and `season` (drop='first')
- **Numerical scaling**: StandardScaler for all numerical features
- **Missing values**: None found in the dataset

### 4. Train-Test Split
- **Split ratio**: 80/20
- **Random state**: 42
- **Training set**: 13,548 samples
- **Test set**: 3,388 samples
- **Processed feature dimensions**: 38 (after one-hot encoding)

## Models Trained

Six different machine learning models were trained and evaluated:

1. **Linear Regression** (Baseline)
2. **Ridge Regression** (L2 regularization, α=1.0)
3. **Lasso Regression** (L1 regularization, α=1.0)
4. **Random Forest** (100 trees, random_state=42)
5. **Gradient Boosting** (100 estimators, random_state=42)
6. **XGBoost** (100 estimators, random_state=42)

## Model Performance

### Performance Metrics

All models were evaluated using:
- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Squared Error)
- **R²** (Coefficient of Determination)

### Results Summary

| Model | Train MAE | Train RMSE | Train R² | Test MAE | Test RMSE | Test R² |
|-------|-----------|------------|----------|----------|-----------|---------|
| **RandomForest** | 11.03 | 14.97 | 0.963 | **29.19** | **39.37** | **0.764** |
| **XGBoost** | 17.78 | 23.46 | 0.909 | 30.33 | 40.30 | 0.753 |
| **GradientBoosting** | 33.98 | 43.80 | 0.681 | 34.31 | 45.24 | 0.689 |
| **Ridge** | 43.96 | 56.69 | 0.466 | 44.64 | 57.99 | 0.488 |
| **LinearRegression** | 43.96 | 56.69 | 0.466 | 44.64 | 57.99 | 0.488 |
| **Lasso** | 43.88 | 57.07 | 0.459 | 44.60 | 58.30 | 0.483 |

### Best Model: Random Forest

**Selected Model**: Random Forest Regressor

**Performance**:
- **Test RMSE**: 39.37 μg/m³
- **Test MAE**: 29.19 μg/m³
- **Test R²**: 0.764 (76.4% variance explained)

**Key Observations**:
- Random Forest shows the best generalization with lowest test RMSE
- Good balance between train and test performance (no severe overfitting)
- XGBoost is a close second with similar performance
- Linear models (Linear Regression, Ridge, Lasso) show similar performance, indicating limited linear relationships
- Gradient Boosting performs moderately well

## Experiment Tracking with MLflow

### Setup
- **Tracking URI**: `file:///C:/Users/robot/Desktop/Delhi-NCR-AQI-Assessment/mlruns`
- **Experiment Name**: `PM2.5_Discrepancy_Prediction`
- **Autologging**: Enabled for scikit-learn models

### Logged Information

For each model run, the following were logged:

#### Parameters
- `model_name`: Name of the model
- `train_size`: Number of training samples
- `test_size`: Number of test samples

#### Metrics
- `train_mae`, `train_rmse`, `train_r2`: Training set metrics
- `test_mae`, `test_rmse`, `test_r2`: Test set metrics
- `feature_importance_*`: Top 10 feature importances (for tree-based models)

#### Artifacts
- **Model files**: Saved models for each run
- **Plots**: 
  - Residual plots (predicted vs residuals)
  - Predicted vs Actual scatter plots

### Feature Importance Logging

For tree-based models (Random Forest, Gradient Boosting, XGBoost), the top 10 most important features were logged as MLflow metrics. Feature names were sanitized to comply with MLflow naming requirements (replacing commas and special characters with underscores).

## Model Artifacts

### Saved Models
- **MLflow**: All models saved in MLflow runs
- **Local**: Best model saved as `models/best_model.pkl`
- **Pipeline**: Complete preprocessing + model pipeline saved

### Results File
- **Location**: `model_results.csv` (project root)
- **Content**: Performance metrics for all models

### Visualization Plots
- Residual plots for each model
- Predicted vs Actual scatter plots
- Saved as: `plots_{model_name}.png`

## Model Pipeline

The final model consists of:

1. **Preprocessing Pipeline**:
   - StandardScaler for numerical features
   - OneHotEncoder for categorical features (location, season)

2. **Model**: Random Forest Regressor
   - n_estimators: 100
   - random_state: 42
   - n_jobs: -1 (parallel processing)

3. **Complete Pipeline**: `Pipeline([('preprocessor', preprocessor), ('model', model)])`

## Key Findings

### 1. Feature Importance
Tree-based models (Random Forest, XGBoost) were able to capture non-linear relationships and feature interactions that linear models could not.

### 2. Model Selection
Random Forest was selected as the best model due to:
- Lowest test RMSE (39.37 μg/m³)
- Good generalization (train R²: 0.963, test R²: 0.764)
- Interpretability through feature importance
- Robust performance

### 3. Data Characteristics
- No missing values in the dataset
- All PM2.5 values within realistic range (no filtering needed)
- Good feature diversity (satellite, ground, hyperlocal, temporal, ratios)

### 4. Limitations
- Linear models show similar performance, suggesting limited linear relationships
- Some overfitting in tree-based models (train R² much higher than test R²)
- Scaling factor (50.0) for Aerosol Index is approximate and may need domain-specific tuning

## Usage

### Making Predictions

The notebook includes helper functions for making predictions:

```python
# Predict discrepancy
predicted_diff = predict_discrepancy(model_pipeline, features_df)

# Predict corrected PM2.5
corrected_pm25 = predict_corrected_pm25(
    model_pipeline, 
    features_df, 
    satellite_value,  # Aerosol_Index_satellite value
    scaling_factor=50.0
)
```

### Loading the Model

```python
import joblib

# Load the saved pipeline
model = joblib.load('models/best_model.pkl')

# Make predictions
predictions = model.predict(features_df)
```

## Technical Details

### Environment
- **Python**: 3.13.5
- **Key Libraries**:
  - scikit-learn: 1.7.2
  - pandas: 2.3.3
  - numpy: 2.3.5
  - mlflow: 3.6.0
  - xgboost: 3.1.2
  - matplotlib: 3.10.7
  - seaborn: 0.13.2

### Reproducibility
- Random seed: 42 (set for numpy and all models)
- Train-test split: random_state=42
- All models use random_state=42

### File Structure
```
Delhi-NCR-AQI-Assessment/
├── notebooks/
│   └── model-training/
│       ├── MLFLOW_Discrepancy_Prediction.ipynb
│       └── cleaned_aqi_merged_dataset.csv
├── models/
│   └── best_model.pkl
├── mlruns/
│   └── [MLflow experiment runs]
├── model_results.csv
└── docs/
    └── Phase_4_Model_Building.md
```

## Future Improvements

1. **Hyperparameter Tuning**: Use GridSearchCV or RandomizedSearchCV to optimize model parameters
2. **Feature Engineering**: 
   - Explore polynomial features
   - Create interaction features
   - Time-series features (lag, rolling averages)
3. **Model Ensembles**: Combine multiple models (e.g., Random Forest + XGBoost)
4. **Cross-Validation**: Implement k-fold cross-validation for more robust evaluation
5. **Scaling Factor Optimization**: Tune the Aerosol Index to PM2.5 conversion factor
6. **Feature Selection**: Use feature importance to reduce dimensionality
7. **Advanced Models**: Try neural networks or other deep learning approaches
8. **Domain Knowledge**: Incorporate meteorological data, seasonal patterns more explicitly

## Conclusion

The Random Forest model successfully predicts PM2.5 discrepancy with an R² of 0.764, demonstrating that machine learning can effectively model the relationship between ground measurements and satellite-derived proxies. The model can be used to correct satellite estimates and improve air quality monitoring in areas with limited ground stations.

---

**Document Created**: November 2025  
**Notebook**: `notebooks/model-training/MLFLOW_Discrepancy_Prediction.ipynb`  
**Best Model**: Random Forest Regressor  
**Test R²**: 0.764

