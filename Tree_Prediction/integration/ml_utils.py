import joblib
import numpy as np
import pandas as pd
import os
import warnings
from django.conf import settings

class TreeSurvivalPredictor:
    """Tree survival prediction utility for MsituGuard
    
    Uses GradientBoosting Classifier (77.3% accuracy)
    Trained on 10,000+ Kenyan tree planting records
    Features: 16 environmental + engineered factors
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.encoders = None
        self.feature_columns = None
        self.load_model()
    
    def load_model(self):
        """Load trained GradientBoosting model and preprocessing components"""
        try:
            try:
                model_dir = os.path.join(settings.BASE_DIR, 'Tree_Prediction', 'training', 'models')
            except:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                model_dir = os.path.join(current_dir, '..', 'training', 'models')
            
            self.model = joblib.load(os.path.join(model_dir, 'tree_survival_model.pkl'))
            self.scaler = joblib.load(os.path.join(model_dir, 'tree_scaler.pkl'))
            self.encoders = joblib.load(os.path.join(model_dir, 'tree_encoders.pkl'))
            self.feature_columns = joblib.load(os.path.join(model_dir, 'feature_columns.pkl'))
            
            print(f"[OK] GradientBoosting model loaded successfully from {model_dir}")
            print(f"  Model accuracy: 77.3%")
            print(f"  Features: {len(self.feature_columns)} (including engineered features)")
            
        except Exception as e:
            print(f"[ERROR] Error loading model: {e}")
            self.model = None
    
    def predict_step7(self, user_input, playbook_features):
        """
        Full Step 7 prediction:
        - user_input: dict with planting_method, care_level, water_source, tree_age_months
        - playbook_features: dict with auto-filled features (soil, rainfall, temp, altitude, soil_ph, region, etc.)
        Returns:
            survival probability (0-1)
        """
        # Merge user input + playbook features
        tree_data = {**playbook_features, **user_input}

        # Convert tuple/list ranges to averages if present
        rainfall = tree_data['rainfall_mm']
        if isinstance(rainfall, (list, tuple)):
            rainfall = sum(rainfall)/len(rainfall)

        temperature = tree_data['temperature_c']
        if isinstance(temperature, (list, tuple)):
            temperature = sum(temperature)/len(temperature)

        # Engineered features
        tree_data['rainfall_mm'] = rainfall
        tree_data['temperature_c'] = temperature
        tree_data['water_balance'] = rainfall - (temperature * 20)
        tree_data['is_high_altitude'] = 1 if tree_data['altitude_m'] > 1500 else 0
        tree_data['soil_acidity'] = 1 if tree_data['soil_ph'] < 6.5 else 0

        # Prepare DataFrame
        input_df = pd.DataFrame([tree_data])

        # Map playbook/user keys to encoder keys
        encoder_key_map = {
            'tree_species': 'species',
            'soil_type': 'soil_type',
            'planting_season': 'planting_season',
            'planting_method': 'planting_method',
            'care_level': 'care_level',
            'water_source': 'water_source',
            'region': 'region',
            'county': 'county'
        }

        # Encode categorical variables using encoders
        for col, enc in self.encoders.items():
            tree_key = next((k for k, v in encoder_key_map.items() if v == col), None)
            key_encoded = f"{col}_encoded"
            if tree_key and tree_key in tree_data:
                try:
                    input_df[key_encoded] = enc.transform([tree_data[tree_key]])[0]
                except:
                    input_df[key_encoded] = 0  # fallback for unknown category
            else:
                input_df[key_encoded] = 0  # fallback for missing key

        # Ensure all required feature columns exist
        for col in self.feature_columns:
            if col not in input_df.columns:
                input_df[col] = 0

        # Select features
        X = input_df[self.feature_columns]

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict survival probability while suppressing sklearn warning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            survival_prob = self.model.predict_proba(X_scaled)[:, 1][0]

        # Return survival probability
        return survival_prob

    def predict_for_user(self, county, species, planting_method, care_level, water_source, tree_age_months=0, playbook=None):
        """
        Step 7 + Step 8 wrapper:
        - Auto-fills features from playbook
        - Returns:
            survival probability (0-1)
            after-care guide (list of instructions)
        """
        if playbook is None:
            raise ValueError("Playbook data must be provided.")

        # Get playbook info for the species
        if species not in playbook:
            raise ValueError(f"Species '{species}' not found in playbook.")

        species_info = playbook[species]

        # Auto-fill features from playbook
        playbook_features = {
            'tree_species': species,
            'soil_type': species_info['Soil'],
            'rainfall_mm': species_info['Rainfall'],
            'temperature_c': species_info['Temperature'],
            'altitude_m': species_info.get('Altitude', 1200),  # default if not in playbook
            'soil_ph': species_info.get('Soil_pH', 6.8),
            'region': species_info.get('Region', 'Unknown'),
            'county': county
        }

        # User input dict
        user_input = {
            'planting_method': planting_method,
            'care_level': care_level,
            'water_source': water_source,
            'tree_age_months': tree_age_months
        }

        # Step 7 prediction
        survival_prob = self.predict_step7(user_input, playbook_features)

        # Step 8 after-care guide from playbook
        after_care = species_info.get('Care Instructions', [])

        return survival_prob, after_care

# Global predictor instance
tree_predictor = TreeSurvivalPredictor()
