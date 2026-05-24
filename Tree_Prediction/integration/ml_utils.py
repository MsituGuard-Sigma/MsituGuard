import os
from django.conf import settings
from .weather_service import WeatherService

MODEL_VERSION = "v2.0.0"

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
        self.model             = None
        self.encoders          = None
        self.feature_columns   = None
        self.species_env_compat      = {}
        self.species_method_pref     = {}
        self.load_model()

    # ------------------------------------------------------------------
    # MODEL LOADING
    # ------------------------------------------------------------------

    def load_model(self):
        """Load trained model and preprocessing components."""
        if not ML_AVAILABLE:
            print("[ML] Libraries not available — demo mode")
            self.model = None
            self._setup_fallback_data()
            return

        try:
            model_dir = os.path.join(
                settings.BASE_DIR, 'Tree_Prediction', 'training', 'models'
            )

            self.model           = joblib.load(os.path.join(model_dir, 'tree_survival_model.pkl'))
            self.encoders        = joblib.load(os.path.join(model_dir, 'tree_encoders.pkl'))
            self.feature_columns = joblib.load(os.path.join(model_dir, 'feature_columns.pkl'))

            # Load lookup tables saved during training
            compat_path = os.path.join(model_dir, 'species_env_compat.pkl')
            method_path = os.path.join(model_dir, 'species_method_pref.pkl')
            if os.path.exists(compat_path):
                self.species_env_compat  = joblib.load(compat_path)
            if os.path.exists(method_path):
                self.species_method_pref = joblib.load(method_path)

            print(f"[ML] Model loaded successfully — {MODEL_VERSION}")

        except Exception as e:
            print(f"[ML] Error loading model: {e}")
            print("[ML] Falling back to demo predictions")
            self.model = None
            self._setup_fallback_data()

    def _setup_fallback_data(self):
        self.fallback_species = [
            'Eucalyptus', 'Pine', 'Acacia', 'Cypress', 'Cedar',
            'Grevillea', 'Neem', 'Wattle', 'Bamboo', 'Casuarina',
            'Jacaranda', 'Indigenous Mix'
        ]

    # ------------------------------------------------------------------
    # WEATHER
    # ------------------------------------------------------------------

    def get_live_weather_data(self, county_name, lat=None, lon=None):
        """Get live weather data with fallback to static defaults."""
        if lat is not None and lon is not None:
            live = WeatherService.get_weather(lat, lon)
            if live:
                rain_mm_hour = float(live.get('rainfall', 0.0) or 0.0)
                return {
                    'temperature_c':     live['temperature'],
                    'rain_mm_hour':      rain_mm_hour,
                    'rainfall':          rain_mm_hour,
                    'rainfall_mm':       rain_mm_hour * 24,
                    'humidity':          live['humidity'],
                    'wind_speed':        live['wind_speed'],
                    'weather_condition': live['weather_main'],
                    'is_live':           True,
                }

        return {
            'temperature_c': 22.0, 'rain_mm_hour': 0.0,
            'rainfall': 0.0, 'rainfall_mm': 2.0,
            'humidity': 65, 'wind_speed': 2.0,
            'weather_condition': 'Clear', 'is_live': False,
        }

    # ------------------------------------------------------------------
    # CORE PREDICTION
    # ------------------------------------------------------------------

    def predict_survival(self, tree_data):
        """
        Predict tree survival probability.

        Args:
            tree_data (dict): Tree planting inputs including species, county,
                              climate/environment values, care level, etc.
        Returns:
            dict: Prediction result with probability, recommendation, risks.
        """
        county = tree_data.get('county')
        lat    = tree_data.get('latitude')
        lon    = tree_data.get('longitude')

        weather = None
        if tree_data.get('use_live_weather', False):
            weather = self.get_live_weather_data(county, lat, lon)
            tree_data['rainfall_mm']   = weather['rainfall_mm']
            tree_data['temperature_c'] = weather['temperature_c']
            tree_data['humidity']      = weather.get('humidity')
            tree_data['wind_speed']    = weather.get('wind_speed')

        if not self.model:
            print("[ML] WARN: model not loaded — using demo fallback")
            return self._demo_prediction(tree_data, weather)

        try:
            return self._ml_prediction(tree_data, weather)
        except Exception as e:
            print(f"[ML] Prediction error: {e} — using demo fallback")
            return self._demo_prediction(tree_data, weather)

    def _ml_prediction(self, tree_data, weather):
        """Run the actual ML model."""
        input_data = pd.DataFrame([tree_data])

        # --- encode categoricals ---
        encode_map = {
            'tree_species':    'species',
            'region':          'region',
            'county':          'county',
            'soil_type':       'soil_type',
            'planting_season': 'planting_season',
            'planting_method': 'planting_method',
            'care_level':      'care_level',
            'water_source':    'water_source',
            'climate_zone':    'climate_zone',
            'temp_category':   'temp_category',
        }
        for col, key in encode_map.items():
            try:
                val = tree_data.get(col, '')
                input_data[col + '_enc'] = self.encoders[key].transform([val])[0]
            except (ValueError, KeyError):
                input_data[col + '_enc'] = 0

        # --- engineered features ---
        # IMPORTANT: thresholds here MUST match train_tree_model.py exactly
        rainfall    = float(tree_data.get('rainfall_mm',   600))
        temperature = float(tree_data.get('temperature_c',  22))
        altitude    = float(tree_data.get('altitude_m',   1500))
        soil_ph     = float(tree_data.get('soil_ph',        6.5))

        input_data['water_balance']    = rainfall - (temperature * 20)
        input_data['is_high_altitude'] = 1 if altitude > 1500 else 0   # matches training
        input_data['soil_acidity']     = 1 if soil_ph < 6.5 else 0

        # --- species-environment compatibility ---
        species      = tree_data.get('tree_species', '')
        climate_zone = tree_data.get('climate_zone', 'Sub_Humid')
        input_data['species_env_compat'] = self.species_env_compat.get(
            (species, climate_zone), 0.65
        )

        # --- fill any missing feature columns ---
        for col in self.feature_columns:
            if col not in input_data.columns:
                input_data[col] = 0

        X = input_data[self.feature_columns]

        survival_prob = float(self.model.predict_proba(X)[0][1])
        print(f"[ML] {species} in {climate_zone} -> {survival_prob:.3f}")

        return self._build_response(survival_prob, tree_data, weather, demo_mode=False)

    # ------------------------------------------------------------------
    # DEMO FALLBACK  (used only when model cannot load)
    # ------------------------------------------------------------------

    def _demo_prediction(self, tree_data, weather):
        """Rule-based fallback — used ONLY when the ML model fails to load."""
        survival_prob = self._calculate_demo_probability(tree_data)
        return self._build_response(survival_prob, tree_data, weather, demo_mode=True)

    def _calculate_demo_probability(self, tree_data):
        """Heuristic estimate — less accurate than the ML model."""
        base = 0.65

        county = tree_data.get('county', '')
        lat    = tree_data.get('latitude')
        lon    = tree_data.get('longitude')

        weather_data = self.get_live_weather_data(county, lat, lon)
        from .weather_normalizer import normalize_rainfall
        rain_info   = normalize_rainfall(weather_data)
        rainfall    = float(rain_info.get('daily_rain_mm', tree_data.get('rainfall_mm', 2.0)))
        temperature = float(weather_data.get('temperature_c', tree_data.get('temperature_c', 22.0)))
        humidity    = float(weather_data.get('humidity', 65))
        altitude    = float(tree_data.get('altitude_m', 1500))
        soil_ph     = float(tree_data.get('soil_ph', 6.5))
        species     = tree_data.get('tree_species', '')

        if rainfall < 1:       base -= 0.15
        elif rainfall < 5:     base -= 0.08
        elif 5 <= rainfall <= 15: base += 0.10
        elif rainfall > 25:    base -= 0.05

        if humidity < 40:      base -= 0.08
        elif humidity > 85:    base += 0.05

        if temperature > 32:   base -= 0.20
        elif temperature > 28: base -= 0.10
        elif 18 <= temperature <= 25: base += 0.10
        elif temperature < 15: base -= 0.08

        if altitude > 2000:    base -= 0.10
        elif 1200 <= altitude <= 1800: base += 0.08
        elif altitude < 500:   base -= 0.05

        if soil_ph < 5.5 or soil_ph > 8.0: base -= 0.12
        elif 6.0 <= soil_ph <= 7.0:         base += 0.05

        # species-env compat via lookup table
        climate_zone = tree_data.get('climate_zone', 'Sub_Humid')
        compat = self.species_env_compat.get((species, climate_zone), 0.65)
        base += (compat - 0.65) * 0.4  # scale influence

        care_bonus = {'High': 0.12, 'Medium': 0.05, 'Low': -0.08}
        base += care_bonus.get(tree_data.get('care_level', 'Medium'), 0)

        import hashlib
        h = int(hashlib.md5(f"{county}{species}".encode()).hexdigest()[:8], 16)
        base += (h % 100 - 50) / 1000

        return max(0.20, min(0.95, base))

    # ------------------------------------------------------------------
    # RESPONSE BUILDER
    # ------------------------------------------------------------------

    def _build_response(self, survival_prob, tree_data, weather, demo_mode):
        species  = tree_data.get('tree_species', '')
        county   = tree_data.get('county', '')
        care     = tree_data.get('care_level', 'Medium')
        season   = tree_data.get('planting_season', '')
        method   = tree_data.get('planting_method', 'Seedling')

        recommendation  = self._get_recommendation(survival_prob, species, care)
        risk_level      = self._get_risk_level(survival_prob)
        confidence      = self._get_confidence_level(survival_prob * 100)
        risks           = self._identify_risks(tree_data)
        reasons         = self._explain_prediction(tree_data, survival_prob)
        weather_used    = bool(weather and weather.get('is_live'))

        if demo_mode:
            print(f"[ML] Demo mode: {species} -> {survival_prob:.3f}")

        return {
            'success':             True,
            'survival_probability': round(survival_prob * 100, 1),
            'confidence_level':     confidence,
            'prediction':          'Likely to Survive' if survival_prob >= 0.6 else 'High Risk',
            'recommendation':       recommendation,
            'risk_level':           risk_level,
            'risks':                risks,
            'reasons':              reasons,
            'model_version':        MODEL_VERSION,
            'demo_mode':            demo_mode,
            'weather_used':         weather_used,
        }

    # ------------------------------------------------------------------
    # SPECIES RECOMMENDATIONS
    # ------------------------------------------------------------------

    def get_species_recommendations(self, location_data):
        """
        Return top species for a location, each with the best planting method.

        The method recommendation uses a two-step logic:
          1. If ML scores differ by more than 2 percentage points between
             methods, pick the highest-scoring method.
          2. Otherwise, use the species agronomic preference from
             SPECIES_METHOD_PREFERENCE — so users always get a meaningful
             answer rather than 'Seedling (default — methods score similarly)'.
        """
        species_list = [
            'Eucalyptus', 'Pine', 'Acacia', 'Cypress', 'Cedar',
            'Grevillea', 'Neem', 'Wattle', 'Bamboo', 'Casuarina',
            'Jacaranda', 'Indigenous Mix'
        ]
        recommendations = []

        for species in species_list:
            best_prob   = None
            best_method = self.species_method_pref.get(species, 'Seedling')

            # Try each planting method to find the best ML score
            method_scores = {}
            for method in ['Seedling', 'Direct Seeding', 'Cutting']:
                test_data = {
                    **location_data,
                    'tree_species':    species,
                    'tree_age_months': 12,
                    'care_level':      'Medium',
                    'planting_method': method,
                }
                try:
                    result = self.predict_survival(test_data)
                    if result['success']:
                        method_scores[method] = result['survival_probability']
                except Exception:
                    continue

            if not method_scores:
                continue

            # Pick method: if ML found a clear winner (>2% spread) use it,
            # else use the agronomic preference
            scores     = list(method_scores.values())
            best_score = max(scores)
            spread     = max(scores) - min(scores)

            if spread > 2.0:
                best_method = max(method_scores, key=method_scores.get)
            # else keep species_method_pref default set above

            recommendations.append({
                'species':              species,
                'survival_probability': best_score,
                'recommended_method':   best_method,
                'risk_level':           self._get_risk_level(best_score / 100),
            })

        recommendations.sort(key=lambda x: x['survival_probability'], reverse=True)
        return recommendations[:5]

    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------

    def _get_recommendation(self, prob, species, care):
        if prob >= 0.80:
            return (f"Excellent conditions for {species}! "
                    f"High survival expected with {care.lower()} care.")
        elif prob >= 0.65:
            return (f"Good conditions for {species}. "
                    f"Consider high care level for better results.")
        elif prob >= 0.45:
            return (f"Moderate risk for {species}. "
                    f"Recommend high care level and consider alternative species.")
        else:
            return ("High risk conditions. "
                    "Consider a different species, location, or wait for a better season.")

    def _get_risk_level(self, prob):
        score = prob * 100 if prob <= 1 else prob
        if score >= 70:   return "Low Risk – Good Conditions"
        elif score >= 50: return "Moderate Risk – Extra Care Needed"
        else:             return "High Risk – Challenging Conditions"

    def _get_confidence_level(self, score):
        if score >= 80:   return "Very High"
        elif score >= 65: return "High"
        elif score >= 50: return "Moderate"
        else:             return "Low"

    def _identify_risks(self, tree_data):
        risks   = []
        season  = tree_data.get('planting_season', '')
        species = tree_data.get('tree_species', '')
        county  = tree_data.get('county', '')
        climate = tree_data.get('climate_zone', '')

        if 'Dry' in season:
            risks.append("Dry season planting increases water stress")

        if species in ['Pine', 'Cypress', 'Cedar', 'Bamboo'] and climate == 'Extremely_Arid':
            risks.append(f"{species} has low compatibility with arid conditions")

        if species == 'Neem' and county in ['Nyeri', 'Meru', 'Nakuru']:
            risks.append("Neem may not tolerate highland cold")

        care = tree_data.get('care_level', 'Medium')
        if care == 'Low':
            risks.append("Low care level significantly reduces survival odds")

        return risks

    def _explain_prediction(self, tree_data, prob):
        reasons = []
        species = tree_data.get('tree_species', '')
        climate = tree_data.get('climate_zone', '')
        care    = tree_data.get('care_level', 'Medium')
        county  = tree_data.get('county', '')

        compat = self.species_env_compat.get((species, climate), 0.65)
        if compat >= 0.85:
            reasons.append(f"{species} is well-suited to {climate} conditions")
        elif compat <= 0.40:
            reasons.append(f"{species} is poorly matched to {climate} conditions")

        if care == 'High':
            reasons.append("High care level significantly improves survival chances")

        if species == 'Indigenous Mix':
            reasons.append("Native species are naturally adapted to local conditions")

        season = tree_data.get('planting_season', '')
        if season == 'Wet':
            reasons.append("Wet season planting gives the best start")

        return reasons

    def is_soil_ideal(self, county, species):
        highland_counties = ['Nyeri', 'Meru', 'Nakuru', 'Kiambu']
        highland_species  = ['Pine', 'Cypress', 'Grevillea', 'Cedar']
        if species in highland_species and county in highland_counties:
            return True
        if species == 'Neem' and county not in highland_counties:
            return True
        return False

    def has_good_rainfall(self, county, species):
        return county in ['Meru', 'Nyeri', 'Kiambu', 'Nakuru']

    def has_high_county_success(self, county, species):
        success_map = {
            'Nyeri':    ['Pine', 'Indigenous Mix', 'Cypress'],
            'Meru':     ['Indigenous Mix', 'Grevillea', 'Pine'],
            'Nakuru':   ['Pine', 'Cypress', 'Indigenous Mix'],
            'Machakos': ['Indigenous Mix', 'Neem'],
            'Mombasa':  ['Neem', 'Indigenous Mix'],
        }
        return species in success_map.get(county, [])


# Global predictor instance
tree_predictor = TreeSurvivalPredictor()