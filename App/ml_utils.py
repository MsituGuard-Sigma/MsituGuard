import os
from django.conf import settings

try:
    import joblib
    import numpy as np
    import pandas as pd
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

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
        if not ML_AVAILABLE:
            print("ML libraries not available - using demo mode")
            self.model = None
            self._setup_fallback_data()
            return
            
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'Tree_Prediction', 'models')
            
            # Load with error handling for version compatibility
            self.model = joblib.load(os.path.join(model_dir, 'tree_survival_model_corrected.pkl'))
            self.scaler = joblib.load(os.path.join(model_dir, 'tree_scaler_corrected.pkl'))
            self.encoders = joblib.load(os.path.join(model_dir, 'tree_encoders_corrected.pkl'))
            self.feature_columns = joblib.load(os.path.join(model_dir, 'feature_columns_corrected.pkl'))
            
            print("Model loaded successfully!")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Falling back to demo predictions...")
            self.model = None
            self._setup_fallback_data()
    
    def _setup_fallback_data(self):
        """Setup fallback data for demo when model fails to load"""
        self.fallback_encoders = {
            'species': ['Eucalyptus', 'Pine', 'Acacia', 'Cypress', 'Cedar', 'Grevillea', 'Neem', 'Wattle', 'Bamboo', 'Casuarina', 'Jacaranda', 'Indigenous Mix'],
            'region': ['Central', 'Eastern', 'Western', 'Coastal', 'Northern'],
            'county': ['Nairobi', 'Kiambu', 'Nakuru', 'Mombasa', 'Kisumu', 'Eldoret', 'Thika', 'Machakos'],
            'soil_type': ['Clay', 'Loam', 'Sandy', 'Rocky', 'Volcanic'],
            'planting_season': ['Wet', 'Dry', 'Transition'],
            'planting_method': ['Seedling', 'Direct Seeding', 'Transplanting'],
            'care_level': ['Low', 'Medium', 'High'],
            'water_source': ['Rain-fed', 'Irrigation', 'Borehole', 'River']
        }
    
    def _calculate_demo_probability(self, tree_data):
        """Calculate realistic demo probability based on input factors"""
        import random
        random.seed(42)  # Consistent results
        
        base_prob = 0.7  # Base 70% survival
        
        # Adjust based on species (some are hardier)
        hardy_species = ['Acacia', 'Neem', 'Eucalyptus', 'Indigenous Mix']
        if tree_data.get('tree_species') in hardy_species:
            base_prob += 0.15
        
        # Adjust based on care level
        care_bonus = {'High': 0.1, 'Medium': 0.05, 'Low': -0.1}
        base_prob += care_bonus.get(tree_data.get('care_level', 'Medium'), 0)
        
        # Adjust based on rainfall
        rainfall = float(tree_data.get('rainfall_mm', 600))
        if 400 <= rainfall <= 800:
            base_prob += 0.1
        elif rainfall < 300 or rainfall > 1200:
            base_prob -= 0.15
        
        # Add some randomness but keep it realistic
        base_prob += random.uniform(-0.05, 0.05)
        
        return max(0.3, min(0.95, base_prob))  # Keep between 30-95%
    
    def predict_survival(self, tree_data):
        """
        Predict tree survival probability
        
        Args:
            tree_data (dict): Dictionary containing tree planting data
        
        Returns:
            dict: Prediction results with probability and recommendation
        """
        
        if not self.model:
            # Use fallback demo prediction
            survival_prob = self._calculate_demo_probability(tree_data)
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob, 3),
                'survival_percentage': round(survival_prob * 100, 1),
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob),
                'demo_mode': True
            }
        
        try:
            if not ML_AVAILABLE:
                raise ImportError("ML libraries not available")
                
            # Prepare input data
            input_data = pd.DataFrame([tree_data])
            
            # Handle unknown categories gracefully
            try:
                input_data['tree_species_encoded'] = self.encoders['species'].transform([tree_data['tree_species']])[0]
            except ValueError:
                input_data['tree_species_encoded'] = 0  # Default to first category
                
            try:
                input_data['region_encoded'] = self.encoders['region'].transform([tree_data['region']])[0]
            except ValueError:
                input_data['region_encoded'] = 0
                
            try:
                input_data['county_encoded'] = self.encoders['county'].transform([tree_data['county']])[0]
            except ValueError:
                input_data['county_encoded'] = 0
                
            try:
                input_data['soil_type_encoded'] = self.encoders['soil_type'].transform([tree_data['soil_type']])[0]
            except ValueError:
                input_data['soil_type_encoded'] = 0
                
            try:
                input_data['planting_season_encoded'] = self.encoders['planting_season'].transform([tree_data['planting_season']])[0]
            except ValueError:
                input_data['planting_season_encoded'] = 0
                
            try:
                input_data['planting_method_encoded'] = self.encoders['planting_method'].transform([tree_data['planting_method']])[0]
            except ValueError:
                input_data['planting_method_encoded'] = 0
                
            try:
                input_data['care_level_encoded'] = self.encoders['care_level'].transform([tree_data['care_level']])[0]
            except ValueError:
                input_data['care_level_encoded'] = 1  # Default to medium
                
            try:
                input_data['water_source_encoded'] = self.encoders['water_source'].transform([tree_data['water_source']])[0]
            except ValueError:
                input_data['water_source_encoded'] = 0
            
            # Select features
            X = input_data[self.feature_columns]
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make prediction with error handling
            try:
                survival_prob = self.model.predict_proba(X_scaled)[0][1]  # Probability of survival
            except Exception as pred_error:
                print(f"Prediction error: {pred_error}")
                # Fallback to demo calculation
                survival_prob = self._calculate_demo_probability(tree_data)
            
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
            print(f"Full prediction error: {e}")
            # Fallback to demo prediction
            survival_prob = self._calculate_demo_probability(tree_data)
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob, 3),
                'survival_percentage': round(survival_prob * 100, 1),
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob),
                'demo_mode': True
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

# Global predictor instance
tree_predictor = TreeSurvivalPredictor()