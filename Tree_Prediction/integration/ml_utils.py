import joblib
import numpy as np
import pandas as pd
import os
from django.conf import settings

class TreeSurvivalPredictor:
    """Tree survival prediction utility for MsituGuard"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.encoders = None
        self.feature_columns = None
        self.load_model()
    
    def load_model(self):
        """Load trained model and preprocessing components"""
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'Tree_Prediction', 'models')
            
            self.model = joblib.load(os.path.join(model_dir, 'tree_survival_model_corrected.pkl'))
            self.scaler = joblib.load(os.path.join(model_dir, 'tree_scaler_corrected.pkl'))
            self.encoders = joblib.load(os.path.join(model_dir, 'tree_encoders_corrected.pkl'))
            self.feature_columns = joblib.load(os.path.join(model_dir, 'feature_columns_corrected.pkl'))
            
            print(f"Model loaded successfully from {model_dir}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            print(f"Attempted to load from: {model_dir}")
            self.model = None
    
    def predict_survival(self, tree_data):
        """
        Predict tree survival probability
        
        Args:
            tree_data (dict): Dictionary containing tree planting data
                - tree_species: str
                - region: str  
                - county: str
                - soil_type: str
                - rainfall_mm: float
                - temperature_c: float
                - altitude_m: float
                - soil_ph: float
                - planting_season: str
                - planting_method: str
                - care_level: str
                - water_source: str
                - tree_age_months: int
        
        Returns:
            dict: Prediction results with probability and recommendation
        """
        
        if not self.model:
            return {
                'success': False,
                'error': 'Model not loaded',
                'survival_probability': 0.5,
                'recommendation': 'Model unavailable - proceed with caution'
            }
        
        try:
            # Prepare input data
            input_data = pd.DataFrame([tree_data])
            
            # Encode categorical variables
            input_data['tree_species_encoded'] = self.encoders['species'].transform([tree_data['tree_species']])[0]
            input_data['region_encoded'] = self.encoders['region'].transform([tree_data['region']])[0]
            input_data['county_encoded'] = self.encoders['county'].transform([tree_data['county']])[0]
            input_data['soil_type_encoded'] = self.encoders['soil_type'].transform([tree_data['soil_type']])[0]
            input_data['planting_season_encoded'] = self.encoders['planting_season'].transform([tree_data['planting_season']])[0]
            input_data['planting_method_encoded'] = self.encoders['planting_method'].transform([tree_data['planting_method']])[0]
            input_data['care_level_encoded'] = self.encoders['care_level'].transform([tree_data['care_level']])[0]
            input_data['water_source_encoded'] = self.encoders['water_source'].transform([tree_data['water_source']])[0]
            
            # Select features
            X = input_data[self.feature_columns]
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make prediction
            survival_prob = self.model.predict_proba(X_scaled)[0][1]  # Probability of survival
            
            # Generate recommendation
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob, 3),
                'survival_percentage': round(survival_prob * 100, 1),
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'survival_probability': 0.5,
                'recommendation': 'Error in prediction - proceed with standard care'
            }
    
    def get_recommendation(self, survival_prob, tree_data):
        """Generate planting recommendation based on survival probability"""
        
        if survival_prob >= 0.8:
            return f"Excellent conditions for {tree_data['tree_species']}! High survival expected with {tree_data['care_level'].lower()} care."
        elif survival_prob >= 0.6:
            return f"Good conditions for {tree_data['tree_species']}. Consider upgrading to high care level for better results."
        elif survival_prob >= 0.4:
            return f"Moderate risk for {tree_data['tree_species']}. Recommend high care level and consider alternative species."
        else:
            return f"High risk conditions. Consider different species, location, or wait for better season."
    
    def get_risk_level(self, survival_prob):
        """Get risk level based on survival probability"""
        if survival_prob >= 0.8:
            return "Low"
        elif survival_prob >= 0.6:
            return "Medium"
        elif survival_prob >= 0.4:
            return "High"
        else:
            return "Very High"
    
    def get_species_recommendations(self, location_data):
        """Get recommended species for a specific location"""
        
        species_list = ['Eucalyptus', 'Pine', 'Acacia', 'Cypress', 'Cedar', 
                       'Grevillea', 'Neem', 'Wattle', 'Bamboo', 'Casuarina', 
                       'Jacaranda', 'Indigenous Mix']
        
        recommendations = []
        
        for species in species_list:
            test_data = {
                **location_data,
                'tree_species': species,
                'tree_age_months': 12,  # Standard age for comparison
                'care_level': 'Medium',
                'planting_method': 'Seedling'
            }
            
            try:
                result = self.predict_survival(test_data)
                if result['success']:
                    recommendations.append({
                        'species': species,
                        'survival_probability': result['survival_probability'],
                        'risk_level': result['risk_level']
                    })
            except:
                continue
        
        # Sort by survival probability
        recommendations.sort(key=lambda x: x['survival_probability'], reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations

    def get_climate_from_gps(self, latitude, longitude, altitude=None):
        """Get climate data from GPS coordinates using real dataset averages"""
        
        try:
            # Load dataset to get real averages by region
            dataset_path = os.path.join(settings.BASE_DIR, 'Tree_Prediction', 'training', 'cleaned_tree_data_fixed.csv')
            df = pd.read_csv(dataset_path)
            
            # Determine region from coordinates
            region = self._map_coordinates_to_region(latitude, longitude)
            
            # Get real averages from dataset for this region
            region_data = df[df['region'] == region]
            
            if len(region_data) > 0:
                # Calculate averages from real data
                climate_data = {
                    'region': region,
                    'county': region_data['county'].mode().iloc[0],  # Most common county
                    'rainfall_mm': round(region_data['rainfall_mm'].mean()),
                    'temperature_c': round(region_data['temperature_c'].mean(), 1),
                    'altitude_m': altitude if altitude and altitude > 0 else round(region_data['altitude_m'].mean()),
                    'soil_type': region_data['soil_type'].mode().iloc[0],  # Most common soil
                    'soil_ph': round(region_data['soil_ph'].mean(), 1),
                    'planting_season': self._get_current_season()
                }
            else:
                # Fallback to Central region if no data found
                central_data = df[df['region'] == 'Central']
                climate_data = {
                    'region': 'Central',
                    'county': central_data['county'].mode().iloc[0],
                    'rainfall_mm': round(central_data['rainfall_mm'].mean()),
                    'temperature_c': round(central_data['temperature_c'].mean(), 1),
                    'altitude_m': altitude if altitude and altitude > 0 else round(central_data['altitude_m'].mean()),
                    'soil_type': central_data['soil_type'].mode().iloc[0],
                    'soil_ph': round(central_data['soil_ph'].mean(), 1),
                    'planting_season': self._get_current_season()
                }
            
            return climate_data
            
        except Exception as e:
            print(f"Error getting climate data: {e}")
            # Return default values if error
            return {
                'region': 'Central',
                'county': 'Nyeri',
                'rainfall_mm': 635,
                'temperature_c': 20.5,
                'altitude_m': altitude if altitude and altitude > 0 else 1850,
                'soil_type': 'Clay',
                'soil_ph': 6.8,
                'planting_season': self._get_current_season()
            }
    
    def _map_coordinates_to_region(self, lat, lon):
        """Map GPS coordinates to Kenyan regions"""
        
        # Nairobi (includes Kangemi)
        if -1.45 <= lat <= -1.15 and 36.6 <= lon <= 37.1:
            return 'Nairobi'
        # Central
        elif -1.0 <= lat <= 0.5 and 36.5 <= lon <= 37.5:
            return 'Central'
        # Coast
        elif -4.7 <= lat <= -1.6 and 39.0 <= lon <= 41.9:
            return 'Coast'
        # Western
        elif -1.0 <= lat <= 1.5 and 34.0 <= lon <= 35.5:
            return 'Western'
        # Eastern
        elif -3.0 <= lat <= 1.0 and 37.5 <= lon <= 40.0:
            return 'Eastern'
        # Rift Valley
        elif -2.0 <= lat <= 2.0 and 35.0 <= lon <= 37.0:
            return 'Rift Valley'
        # Northern
        elif 1.0 <= lat <= 5.0 and 35.0 <= lon <= 42.0:
            return 'Northern'
        # North Eastern
        elif -1.0 <= lat <= 4.0 and 38.0 <= lon <= 42.0:
            return 'North Eastern'
        # Nyanza
        elif -1.5 <= lat <= 0.5 and 33.8 <= lon <= 35.5:
            return 'Nyanza'
        else:
            return 'Central'  # Default
    
    def _get_current_season(self):
        """Get current planting season based on date"""
        from datetime import datetime
        current_month = datetime.now().month
        
        # Kenya's seasons: Wet (Mar-May, Oct-Dec), Dry (Jun-Sep, Jan-Feb)
        if current_month in [3, 4, 5, 10, 11, 12]:
            return 'Wet'
        elif current_month in [6, 7, 8, 9, 1, 2]:
            return 'Dry'
        else:
            return 'Transition'

# Global predictor instance
tree_predictor = TreeSurvivalPredictor()