"""
Script to load the saved best model and make predictions.

Usage:
    python scripts/load_and_predict.py
    
    Or import in your code:
    from scripts.load_and_predict import load_model, predict_discrepancy, predict_corrected_pm25
"""

import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "best_model_pipeline.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"


def load_model():
    """
    Load the saved model pipeline and metadata.
    
    Returns:
        tuple: (pipeline, metadata) - The loaded model pipeline and metadata dictionary
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Please run the training notebook first to save the model."
        )
    
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Metadata not found at {METADATA_PATH}. "
            "Please run the training notebook first to save the metadata."
        )
    
    print(f"Loading model from {MODEL_PATH}...")
    pipeline = joblib.load(MODEL_PATH)
    
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    
    print("✓ Model loaded successfully!")
    print(f"  Model Type: {metadata['model_name']}")
    print(f"  Test RMSE: {metadata['test_rmse']:.4f}")
    print(f"  Test R²: {metadata['test_r2']:.4f}")
    
    return pipeline, metadata


def predict_discrepancy(pipeline, features_df):
    """
    Predict discrepancy between ground and satellite PM2.5.
    
    Args:
        pipeline: The loaded model pipeline
        features_df: DataFrame with all required feature columns
        
    Returns:
        Array of predicted discrepancies
    """
    return pipeline.predict(features_df)


def predict_corrected_pm25(pipeline, metadata, features_df, satellite_value):
    """
    Predict corrected PM2.5 using satellite value and predicted discrepancy.
    
    Args:
        pipeline: The loaded model pipeline
        metadata: Model metadata dictionary
        features_df: DataFrame with all required feature columns
        satellite_value: Satellite AOD value (Aerosol_Index_satellite)
        
    Returns:
        Array of corrected PM2.5 values
    """
    predicted_diff = predict_discrepancy(pipeline, features_df)
    scaling_factor = metadata['scaling_factor']
    corrected_pm25 = (satellite_value * scaling_factor) + predicted_diff
    return corrected_pm25


def prepare_features(data_dict, metadata):
    """
    Prepare feature DataFrame from a dictionary, ensuring all required columns are present.
    
    Args:
        data_dict: Dictionary with feature values
        metadata: Model metadata dictionary
        
    Returns:
        DataFrame with all required features in correct order
    """
    required_cols = metadata['feature_columns']
    
    # Create DataFrame from dictionary
    df = pd.DataFrame([data_dict])
    
    # Add missing columns with default values
    for col in required_cols:
        if col not in df.columns:
            print(f"Warning: Missing column '{col}', using default value 0")
            df[col] = 0
    
    # Reorder columns to match training data
    df = df[required_cols]
    
    return df


if __name__ == "__main__":
    # Load model
    pipeline, metadata = load_model()
    
    # Example: Create sample data
    print("\n" + "="*60)
    print("Example: Making predictions on new data")
    print("="*60)
    
    sample_data = {
        'NO2_satellite': 0.000191,
        'SO2_satellite': -0.000433,
        'CO_satellite': 0.048550,
        'O3_satellite': 0.164568,
        'location': 'Anand Vihar, Delhi',
        'PM10_ground': 449.58,
        'NO2_ground': 54.76,
        'SO2_ground': 10.5,
        'CO_ground': 2.1,
        'O3_ground': 60.0,
        'lat': 28.65,
        'lon': 77.31,
        'distance_to_major_road': 150.0,
        'total_road_length_m': 5000.0,
        'major_road_length_m': 1000.0,
        'pct_green': 15.5,
        'pct_industrial': 20.0,
        'pct_residential': 40.0,
        'building_density': 0.8,
        'avg_building_area_m2': 800.0,
        'median_building_area_m2': 350.0,
        'building_count': 500.0,
        'major_road_fraction': 0.19,
        'month': 1,
        'day_of_week': 2,
        'season': 'Winter',
        'NO2_ratio': 286676.0,
        'SO2_ratio': -24850.0,
        'CO_ratio': 75.0,
        'O3_ratio': 365.0
    }
    
    # Prepare features
    features_df = prepare_features(sample_data, metadata)
    
    # Make predictions
    satellite_aod = -1.098919  # Example AOD value
    predicted_diff = predict_discrepancy(pipeline, features_df)
    corrected_pm25 = predict_corrected_pm25(pipeline, metadata, features_df, satellite_aod)
    
    print(f"\nPredicted Discrepancy: {predicted_diff[0]:.2f}")
    print(f"Satellite AOD: {satellite_aod}")
    print(f"Corrected PM2.5: {corrected_pm25[0]:.2f}")
    print(f"\n✓ Prediction complete!")
    
    print("\n" + "="*60)
    print("Usage in your code:")
    print("="*60)
    print("""
from scripts.load_and_predict import load_model, predict_discrepancy, predict_corrected_pm25, prepare_features

# Load model once
pipeline, metadata = load_model()

# Prepare your data
your_data = {
    'NO2_satellite': 0.000191,
    'SO2_satellite': -0.000433,
    # ... add all required features
}
features_df = prepare_features(your_data, metadata)

# Make predictions
predicted_diff = predict_discrepancy(pipeline, features_df)
corrected_pm25 = predict_corrected_pm25(pipeline, metadata, features_df, satellite_aod_value)
""")

