import os
from django.conf import settings
from .weather_service import WeatherService

# Model version for tracking
MODEL_VERSION = "v1.2.0"

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
            model_dir = os.path.join(settings.BASE_DIR, 'Tree_Prediction', 'training', 'models')
            
            # Load with error handling for version compatibility
            self.model = joblib.load(os.path.join(model_dir, 'tree_survival_model.pkl'))
            self.scaler = joblib.load(os.path.join(model_dir, 'tree_scaler.pkl'))
            self.encoders = joblib.load(os.path.join(model_dir, 'tree_encoders.pkl'))
            self.feature_columns = joblib.load(os.path.join(model_dir, 'feature_columns.pkl'))
            
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
    
    def get_live_weather_data(self, county_name, lat=None, lon=None):
        """Get live weather data for county with fallback to static data"""
        if lat is not None and lon is not None:
            live_weather = WeatherService.get_weather(lat, lon)
            if live_weather:
                return {
                    'temperature_c': live_weather['temperature'],
                    'rainfall_mm': live_weather['rainfall'] * 24,  # Convert hourly to daily estimate
                    'humidity': live_weather['humidity'],
                    'wind_speed': live_weather['wind_speed'],
                    'weather_condition': live_weather['weather_main']
                }
        
        # Fallback to static county data
        return {
            'temperature_c': 22.0,
            'rainfall_mm': 2.0,
            'humidity': 65,
            'wind_speed': 2.0,
            'weather_condition': 'Clear'
        }
    
    def _calculate_demo_probability(self, tree_data):
        """Calculate realistic demo probability using LIVE weather + county data"""
        
        base_prob = 0.65  # Base survival rate
        
        # Get live weather data if coordinates available
        county = tree_data.get('county', '')
        lat = tree_data.get('latitude')
        lon = tree_data.get('longitude')
        
        weather_data = self.get_live_weather_data(county, lat, lon)
        
        # Normalize rainfall from hourly to daily
        from .weather_normalizer import normalize_rainfall
        rain_info = normalize_rainfall(weather_data)
        
        # Use live weather data
        rainfall = float(rain_info.get('daily_rain_mm', tree_data.get('rainfall_mm', 2.0)))
        temperature = float(weather_data.get('temperature_c', tree_data.get('temperature_c', 22.0)))
        humidity = float(weather_data.get('humidity', 65))
        
        print(f"[WEATHER-ML] Daily rainfall: {rainfall}mm ({rain_info.get('rain_status', 'Unknown')})", flush=True)
        altitude = float(tree_data.get('altitude_m', 1500))
        soil_ph = float(tree_data.get('soil_ph', 6.5))
        
        print(f"[WEATHER-ML] Using live data: {temperature}°C, {rainfall}mm, {humidity}% humidity", flush=True)
        
        # Live weather adjustments (more sensitive to current conditions)
        if rainfall < 1:  # Very dry today
            base_prob -= 0.15
        elif rainfall < 5:  # Dry conditions
            base_prob -= 0.08
        elif 5 <= rainfall <= 15:  # Good moisture
            base_prob += 0.10
        elif rainfall > 25:  # Too wet today
            base_prob -= 0.05
        
        # Humidity impact (new with live weather)
        if humidity < 40:  # Very dry air
            base_prob -= 0.08
        elif humidity > 85:  # Very humid
            base_prob += 0.05
            
        # Temperature impact
        if temperature > 32:  # Very hot (Turkana, Garissa)
            base_prob -= 0.20
        elif temperature > 28:  # Hot
            base_prob -= 0.10
        elif 18 <= temperature <= 25:  # Optimal (Nyeri, Kiambu)
            base_prob += 0.10
        elif temperature < 15:  # Too cold
            base_prob -= 0.08
            
        # Altitude impact
        if altitude > 2000:  # Very high altitude
            base_prob -= 0.10
        elif 1200 <= altitude <= 1800:  # Optimal highland
            base_prob += 0.08
        elif altitude < 500:  # Too low (coastal)
            base_prob -= 0.05
            
        # Soil pH impact
        if soil_ph < 5.5 or soil_ph > 8.0:  # Extreme pH
            base_prob -= 0.12
        elif 6.0 <= soil_ph <= 7.0:  # Optimal pH
            base_prob += 0.05
            
        # Species-specific adjustments
        species = tree_data.get('tree_species', '')
        if species in ['Neem', 'Eucalyptus']:  # Drought tolerant
            if rainfall < 500:
                base_prob += 0.15  # Better in dry conditions
        elif species in ['Pine', 'Cypress']:  # Highland species
            if altitude > 1500:
                base_prob += 0.12  # Better at altitude
        elif species == 'Indigenous Mix':  # Adapted to local conditions
            base_prob += 0.08  # Always gets bonus
            
        # Care level impact
        care_bonus = {'High': 0.12, 'Medium': 0.05, 'Low': -0.08}
        base_prob += care_bonus.get(tree_data.get('care_level', 'Medium'), 0)
        
        # County-specific hash for consistency (same inputs = same output)
        import hashlib
        county_hash = int(hashlib.md5(f"{county}{species}".encode()).hexdigest()[:8], 16)
        variation = (county_hash % 100 - 50) / 1000  # ±0.05 variation
        base_prob += variation
        
        return max(0.25, min(0.92, base_prob))
    
    def predict_survival(self, tree_data):
        """
        Predict tree survival probability
        
        Args:
            tree_data (dict): Dictionary containing tree planting data
        
        Returns:
            dict: Prediction results with probability and recommendation
        """
        
        # FORCE live weather usage before any prediction
        county = tree_data.get('county')
        lat = tree_data.get('latitude')
        lon = tree_data.get('longitude')
        
        weather = self.get_live_weather_data(county, lat, lon)
        tree_data['rainfall_mm'] = weather['rainfall_mm']
        tree_data['temperature_c'] = weather['temperature_c']
        
        if not self.model:
            # Use fallback demo prediction
            survival_prob = self._calculate_demo_probability(tree_data)
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            print(f"[COUNTY DATA] Environmental factors used:")
            print(f"   County: {tree_data.get('county')}")
            print(f"   Rainfall: {tree_data.get('rainfall_mm')}mm")
            print(f"   Temperature: {tree_data.get('temperature_c')}C")
            print(f"   Altitude: {tree_data.get('altitude_m')}m")
            print(f"   Soil pH: {tree_data.get('soil_ph')}")
            print(f"   -> Survival Probability: {survival_prob:.3f}")
            
            # Enhanced response with confidence and explanations
            confidence_level = self.get_confidence_level(survival_prob * 100)
            risks = self.identify_risks(tree_data)
            reasons = self.explain_prediction(tree_data, survival_prob)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob * 100, 1),
                'confidence_level': confidence_level,
                'prediction': "Likely to Survive" if survival_prob >= 0.6 else "High Risk",
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob),
                'risks': risks,
                'reasons': reasons,
                'model_version': MODEL_VERSION,
                'demo_mode': True
            }
        
        try:
            if not ML_AVAILABLE:
                raise ImportError("ML libraries not available")
                
            # Ensure we have live weather data in tree_data
            if 'rainfall_mm' not in tree_data or 'temperature_c' not in tree_data:
                weather = self.get_live_weather_data(county, lat, lon)
                tree_data['rainfall_mm'] = weather['rainfall_mm']
                tree_data['temperature_c'] = weather['temperature_c']
                
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
            
            # Add engineered features that the model expects
            input_data['water_balance'] = tree_data.get('rainfall_mm', 600) - (tree_data.get('temperature_c', 20) * 20)
            input_data['is_high_altitude'] = 1 if tree_data.get('altitude_m', 1500) > 1800 else 0
            input_data['soil_acidity'] = 1 if tree_data.get('soil_ph', 6.5) < 6.0 else 0
            
            # Select features (handle missing columns gracefully)
            available_features = [col for col in self.feature_columns if col in input_data.columns]
            if len(available_features) != len(self.feature_columns):
                # Add missing features with default values
                for col in self.feature_columns:
                    if col not in input_data.columns:
                        input_data[col] = 0
            
            X = input_data[self.feature_columns]
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make prediction with proper DataFrame handling
            try:
                # Ensure we're using DataFrame with proper column names
                X_df = pd.DataFrame(X_scaled, columns=self.feature_columns)
                survival_prob = self.model.predict_proba(X_df)[0][1]  # Probability of survival
                print(f"   ML model prediction successful: {survival_prob:.3f}")
            except Exception as pred_error:
                print(f"   ML prediction error: {pred_error}")
                # Fallback to demo calculation
                survival_prob = self._calculate_demo_probability(tree_data)
            
            # Generate recommendation
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            # Enhanced response with confidence and explanations
            confidence_level = self.get_confidence_level(survival_prob * 100)
            risks = self.identify_risks(tree_data)
            reasons = self.explain_prediction(tree_data, survival_prob)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob * 100, 1),
                'confidence_level': confidence_level,
                'prediction': "Likely to Survive" if survival_prob >= 0.6 else "High Risk",
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob),
                'risks': risks,
                'reasons': reasons,
                'model_version': MODEL_VERSION
            }
            
        except Exception as e:
            print(f"Full prediction error: {e}")
            # Fallback to demo prediction
            survival_prob = self._calculate_demo_probability(tree_data)
            recommendation = self.get_recommendation(survival_prob, tree_data)
            
            # Enhanced response with confidence and explanations
            confidence_level = self.get_confidence_level(survival_prob * 100)
            risks = self.identify_risks(tree_data)
            reasons = self.explain_prediction(tree_data, survival_prob)
            
            return {
                'success': True,
                'survival_probability': round(survival_prob * 100, 1),
                'confidence_level': confidence_level,
                'prediction': "Likely to Survive" if survival_prob >= 0.6 else "High Risk",
                'recommendation': recommendation,
                'risk_level': self.get_risk_level(survival_prob),
                'risks': risks,
                'reasons': reasons,
                'model_version': MODEL_VERSION,
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
        score = survival_prob * 100 if survival_prob <= 1 else survival_prob
        if score >= 70:
            return "Low Risk – Good Conditions"
        elif score >= 50:
            return "Moderate Risk – Extra Care Needed"
        else:
            return "High Risk – Challenging Conditions"
    
    def get_confidence_level(self, score):
        """Get confidence level based on prediction score"""
        if score >= 80:
            return "Very High"
        elif score >= 65:
            return "High"
        elif score >= 50:
            return "Moderate"
        else:
            return "Low"
    
    def identify_risks(self, tree_data):
        """Identify potential risks for tree planting"""
        risks = []
        
        season = tree_data.get('planting_season', '')
        if 'Dry' in season or 'June' in season or 'July' in season or 'August' in season:
            risks.append("Dry season planting increases water stress")
        
        county = tree_data.get('county', '')
        species = tree_data.get('tree_species', '')
        
        # Highland species in lowland areas
        if species in ['Pine', 'Cypress'] and county in ['Mombasa', 'Kilifi', 'Garissa']:
            risks.append("Highland species may struggle in coastal/lowland conditions")
        
        # Lowland species in highland areas
        if species == 'Neem' and county in ['Nyeri', 'Meru', 'Nakuru']:
            risks.append("Lowland species may not tolerate highland cold")
        
        # Soil conditions
        if not self.is_soil_ideal(county, species):
            risks.append("Soil conditions may reduce survival rate")
        
        return risks
    
    def is_soil_ideal(self, county, species):
        """Check if soil conditions are ideal for species"""
        # Simplified soil compatibility check
        highland_counties = ['Nyeri', 'Meru', 'Nakuru', 'Kiambu']
        highland_species = ['Pine', 'Cypress', 'Grevillea']
        
        if species in highland_species and county in highland_counties:
            return True
        if species == 'Neem' and county not in highland_counties:
            return True
        return False
    
    def explain_prediction(self, tree_data, survival_prob):
        """Generate explanation for the prediction"""
        reasons = []
        
        county = tree_data.get('county', '')
        species = tree_data.get('tree_species', '')
        
        # Good rainfall conditions
        if self.has_good_rainfall(county, species):
            reasons.append("Rainfall levels support healthy growth")
        
        # County success rate
        if self.has_high_county_success(county, species):
            reasons.append("This species performs well in this county")
        
        # Species adaptation
        if species == 'Indigenous Mix':
            reasons.append("Native species are naturally adapted to local conditions")
        
        # Care level
        care_level = tree_data.get('care_level', 'Medium')
        if care_level == 'High':
            reasons.append("High care level significantly improves survival chances")
        
        # Season timing
        season = tree_data.get('planting_season', '')
        if 'March' in season or 'April' in season or 'May' in season:
            reasons.append("Planting during rainy season provides optimal conditions")
        
        return reasons
    
    def has_good_rainfall(self, county, species):
        """Check if county has good rainfall for species"""
        high_rainfall_counties = ['Meru', 'Nyeri', 'Kiambu', 'Nakuru']
        return county in high_rainfall_counties
    
    def has_high_county_success(self, county, species):
        """Check if species has high success rate in county"""
        # Simplified success mapping
        success_map = {
            'Nyeri': ['Pine', 'Indigenous Mix', 'Cypress'],
            'Meru': ['Indigenous Mix', 'Grevillea', 'Pine'],
            'Nakuru': ['Pine', 'Cypress', 'Indigenous Mix'],
            'Machakos': ['Indigenous Mix', 'Neem'],
            'Mombasa': ['Neem', 'Indigenous Mix']
        }
        return species in success_map.get(county, [])
    
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