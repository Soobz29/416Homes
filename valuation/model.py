#!/usr/bin/env python3
"""
416Homes Valuation Model

LightGBM model for property valuation based on sold comps.
"""

# Temporarily disabled for Railway deployment (data science stack removed)
try:
    import pandas as pd  # type: ignore
    import numpy as np  # type: ignore
    import lightgbm as lgb  # type: ignore
    from sklearn.model_selection import train_test_split  # type: ignore
    from sklearn.metrics import mean_absolute_percentage_error  # type: ignore
    from sklearn.preprocessing import LabelEncoder  # type: ignore
    _DS_ENABLED = True
except Exception:  # pragma: no cover
    pd = None  # type: ignore
    np = None  # type: ignore
    lgb = None  # type: ignore
    train_test_split = None  # type: ignore
    mean_absolute_percentage_error = None  # type: ignore
    LabelEncoder = None  # type: ignore
    _DS_ENABLED = False
from typing import List, Dict, Any
import joblib
import os
from dotenv import load_dotenv
import logging
import warnings

from supabase import create_client

load_dotenv()
logger = logging.getLogger(__name__)


def market_analysis_from_ppsf(price_per_sqft: float) -> str:
    """Shared market analysis text from price-per-sqft. Toronto 2026 thresholds."""
    if price_per_sqft < 650:
        return "Priced below market value — strong buying opportunity"
    elif price_per_sqft < 900:
        return "Priced competitively for the GTA market"
    elif price_per_sqft < 1100:
        return "Priced above market — room to negotiate"
    else:
        return "Priced significantly above market value"


class ValuationModel:
    """LightGBM-based property valuation model"""
    
    def __init__(self):
        self.model = None
        self.encoders = {}
        self.numeric_medians: Dict[str, float] = {}
        self.feature_columns = [
            'bedrooms', 'bathrooms', 'sqft', 'property_type_encoded',
            'neighbourhood_encoded', 'city_encoded'
        ]
        self.target_column = 'price_per_sqft'
    
    def load_data(self) -> pd.DataFrame:
        """Load training data from Supabase"""
        if not _DS_ENABLED:
            raise RuntimeError("Valuation model disabled for minimal Railway deployment")
        try:
            client = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
            
            # Get sold comps for training
            result = client.table('sold_comps').select('*').execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                logger.info(f"Loaded {len(df)} sold comps for training")
                
                # Data cleaning
                df = self.clean_data(df)
                return df
            else:
                logger.warning("No sold comps data available")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare training data"""
        
        # Remove rows with missing critical values
        df = df.dropna(subset=['price', 'bedrooms', 'bathrooms', 'sqft'])
        
        # Convert numeric columns
        numeric_columns = ['price', 'bedrooms', 'bathrooms', 'sqft']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove outliers and invalid data
        df = df[df['price'] > 10000]  # Remove extremely low prices
        df = df[df['bedrooms'] > 0]
        df = df[df['bathrooms'] > 0]
        df = df[df['sqft'] > 100]
        df = df[df['sqft'] < 10000]  # Remove unrealistic square footage
        
        # Create price per square foot target
        df['price_per_sqft'] = df['price'] / df['sqft']
        
        # Remove extreme outliers
        df = df[df['price_per_sqft'] < 2000]  # Remove extremely high price per sqft
        df = df[df['price_per_sqft'] > 50]  # Remove extremely low price per sqft
        
        logger.info(f"Cleaned dataset: {len(df)} rows remaining")
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for model training"""
        
        df = df.copy()
        
        # Encode categorical variables
        categorical_columns = ['property_type', 'neighbourhood', 'city']
        
        for col in categorical_columns:
            if col in df.columns:
                le = LabelEncoder()
                df[f'{col}_encoded'] = le.fit_transform(df[col].fillna('Unknown'))
                self.encoders[col] = le
        
        # Fill missing values and save medians for prediction-time use
        for col in ['bedrooms', 'bathrooms', 'sqft']:
            median_val = float(df[col].median())
            self.numeric_medians[col] = median_val
            df[col] = df[col].fillna(median_val)
        # Store price_per_sqft median for confidence calculation at inference time
        if 'price_per_sqft' in df.columns:
            self.numeric_medians['price_per_sqft'] = float(df['price_per_sqft'].median())

        return df
    
    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train the LightGBM model"""
        
        if len(df) < 50:
            logger.warning("Insufficient data for training (need at least 50 samples)")
            return {'error': 'Insufficient training data'}
        
        # Prepare features
        df = self.prepare_features(df)
        
        # Split features and target
        X = df[self.feature_columns]
        y = df[self.target_column]
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train LightGBM model
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = lgb.LGBMRegressor(
                objective='regression',
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric='mape',
                callbacks=[
                    lgb.early_stopping(10),
                    lgb.log_evaluation(100)
                ]
            )
            
            self.model = model
            
            # Evaluate model
            y_pred = model.predict(X_val)
            mape = mean_absolute_percentage_error(y_val, y_pred)
            
            logger.info(f"Model trained with validation MAPE: {mape:.2f}%")
            
            return {
                'model': model,
                'mape': mape,
                'feature_importance': dict(zip(self.feature_columns, model.feature_importances_)),
                'training_samples': len(X_train),
                'validation_samples': len(X_val)
            }
    
    def save_model(self, filepath: str = 'valuation_model.pkl'):
        """Save the trained model and encoders"""
        
        if self.model is None:
            logger.error("No model to save")
            return False
        
        try:
            # Save model
            joblib.dump(self.model, filepath)
            
            # Save encoders and numeric medians
            encoders_path = filepath.replace('.pkl', '_encoders.pkl')
            joblib.dump({'encoders': self.encoders, 'numeric_medians': self.numeric_medians}, encoders_path)
            
            logger.info(f"Model saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str = 'valuation_model.pkl'):
        """Load the trained model and encoders"""
        
        try:
            # Load model
            self.model = joblib.load(filepath)
            
            # Load encoders and numeric medians
            encoders_path = filepath.replace('.pkl', '_encoders.pkl')
            saved = joblib.load(encoders_path)
            if isinstance(saved, dict) and 'encoders' in saved:
                self.encoders = saved['encoders']
                self.numeric_medians = saved.get('numeric_medians', {})
            else:
                # Legacy format: just the encoders dict
                self.encoders = saved
            
            logger.info(f"Model loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def predict(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction for a property"""
        
        if self.model is None:
            return {'error': 'Model not loaded'}
        
        try:
            # Prepare input data
            input_df = pd.DataFrame([property_data])
            
            # Encode categorical variables
            for col, encoder in self.encoders.items():
                if col in input_df.columns:
                    # Handle unknown categories
                    value = input_df[col].iloc[0]
                    if value not in encoder.classes_:
                        value = encoder.classes_[0]  # Use first class as default
                    input_df[f'{col}_encoded'] = encoder.transform([value])[0]
            
            # Fill missing values using training-time medians
            for col in ['bedrooms', 'bathrooms', 'sqft']:
                fallback = self.numeric_medians.get(col, 0)
                if col not in input_df.columns:
                    input_df[col] = fallback
                else:
                    input_df[col] = pd.to_numeric(input_df[col], errors='coerce').fillna(fallback)

            # Ensure all encoded columns exist (default to 0 for unseen categoricals)
            for col in ['property_type_encoded', 'neighbourhood_encoded', 'city_encoded']:
                if col not in input_df.columns:
                    input_df[col] = 0

            # Prepare features
            X = input_df[self.feature_columns]

            # Make prediction
            price_per_sqft_pred = self.model.predict(X)

            # Calculate estimated price
            sqft_val = float(input_df['sqft'].iloc[0]) or self.numeric_medians.get('sqft', 1000)
            estimated_price = price_per_sqft_pred[0] * sqft_val

            # Confidence: distance of prediction from the training median $/sqft
            median_ppsf = self.numeric_medians.get('price_per_sqft', 900)
            deviation = abs(price_per_sqft_pred[0] - median_ppsf) / max(median_ppsf, 1)
            confidence = round(min(0.92, max(0.65, 1.0 - deviation * 0.5)), 2)
            
            return {
                'estimated_value': int(estimated_price),
                'confidence': confidence,
                'price_per_sqft': float(price_per_sqft_pred[0]),
                'market_analysis': self.generate_market_analysis(estimated_price, property_data)
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {'error': f'Prediction failed: {str(e)}'}
    
    def generate_market_analysis(self, estimated_price: int, property_data: Dict[str, Any]) -> str:
        """Generate market analysis text"""
        sqft = property_data.get('sqft') or 1000
        try:
            sqft = float(sqft) or 1000
        except (TypeError, ValueError):
            sqft = 1000
        return market_analysis_from_ppsf(estimated_price / sqft)

def main():
    """Main training pipeline"""
    
    logger.info("Starting valuation model training...")
    
    # Initialize model
    valuation_model = ValuationModel()
    
    # Load and prepare data
    df = valuation_model.load_data()
    
    if df.empty:
        logger.error("No data available for training")
        return
    
    # Train model
    training_result = valuation_model.train_model(df)
    
    if 'error' in training_result:
        logger.error(f"Training failed: {training_result['error']}")
        return
    
    # Save model
    if valuation_model.save_model():
        logger.info("Model training completed successfully")
        
        # Print results
        print(f"✅ Model Training Complete")
        print(f"📊 Validation MAPE: {training_result['mape']:.2f}%")
        print(f"🔢 Training samples: {training_result['training_samples']}")
        print(f"✅ Validation samples: {training_result['validation_samples']}")
        print(f"💾 Model saved to valuation_model.pkl")
        
        if training_result['mape'] < 10:
            print("🎯 Model performance: EXCELLENT")
        elif training_result['mape'] < 15:
            print("🎯 Model performance: GOOD")
        else:
            print("⚠️ Model performance: NEEDS IMPROVEMENT")
    else:
        logger.error("Failed to save model")

if __name__ == "__main__":
    main()
