import json
import logging
from .mistral_ai import mistral_ai
from Tree_Prediction.integration.ml_utils import tree_predictor

logger = logging.getLogger(__name__)

class HybridTreePredictor:
    """
    Hybrid predictor that combines RandomForest ML model with MISTRAL AI
    for enhanced prediction accuracy
    """
    
    def __init__(self):
        self.ml_weight = 0.7  # 70% weight to ML model
        self.ai_weight = 0.3  # 30% weight to AI model
    
    def get_ai_prediction(self, tree_data):
        """Get MISTRAL AI prediction for tree survival"""
        
        # Check if MISTRAL AI is available
        if not mistral_ai.api_key:
            print("MISTRAL AI not configured, skipping AI prediction")
            return None
        
        print(f"MISTRAL AI available for hybrid prediction: {bool(mistral_ai.api_key)}")
        
        system_prompt = """You are a Kenyan forestry expert AI. Based on environmental data, predict tree survival probability as a percentage (0-100). Respond with ONLY the number, no explanation."""
        
        user_prompt = f"""
        Predict tree survival percentage for:
        Species: {tree_data.get('tree_species', 'Unknown')}
        Location: {tree_data.get('county', 'Unknown')}, {tree_data.get('region', 'Unknown')}
        Soil: {tree_data.get('soil_type', 'Unknown')} (pH {tree_data.get('soil_ph', 'Unknown')})
        Rainfall: {tree_data.get('rainfall_mm', 'Unknown')}mm/year
        Temperature: {tree_data.get('temperature_c', 'Unknown')}°C
        Altitude: {tree_data.get('altitude_m', 'Unknown')}m
        Season: {tree_data.get('planting_season', 'Unknown')}
        Method: {tree_data.get('planting_method', 'Unknown')}
        
        Respond with only the survival percentage number (e.g., 75):
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = mistral_ai._make_request(messages, max_tokens=10)
            if response:
                # Extract number from response
                import re
                numbers = re.findall(r'\d+', response)
                if numbers:
                    return float(numbers[0]) / 100.0  # Convert to probability
            return None
        except Exception as e:
            logger.error(f"AI prediction failed: {str(e)}")
            return None
    
    def hybrid_predict(self, tree_data):
        """
        Combine ML model and AI predictions for enhanced accuracy
        """
        try:
            # Get ML model prediction
            ml_result = tree_predictor.predict_survival(tree_data)
            ml_probability = ml_result.get('survival_probability', 0.5)
            
            # Get AI prediction
            ai_probability = self.get_ai_prediction(tree_data)
            
            if ai_probability is not None:
                # Weighted ensemble prediction
                hybrid_probability = (
                    self.ml_weight * ml_probability + 
                    self.ai_weight * ai_probability
                )
                
                # Calculate confidence based on agreement
                agreement = 1 - abs(ml_probability - ai_probability)
                confidence = min(0.95, 0.7 + (agreement * 0.25))
                
                prediction_method = "Hybrid ML + AI"
                
                logger.info(f"Hybrid prediction: ML={ml_probability:.3f}, AI={ai_probability:.3f}, Hybrid={hybrid_probability:.3f}")
                
            else:
                # Fallback to ML only if AI fails
                hybrid_probability = ml_probability
                confidence = 0.85
                prediction_method = "ML Only (AI unavailable)"
            
            # Determine risk level
            if hybrid_probability >= 0.75:
                risk_level = "Low"
            elif hybrid_probability >= 0.6:
                risk_level = "Medium"
            elif hybrid_probability >= 0.4:
                risk_level = "High"
            else:
                risk_level = "Very High"
            
            # Generate enhanced recommendation
            recommendation = self.generate_hybrid_recommendation(
                tree_data, hybrid_probability, ml_probability, ai_probability
            )
            
            # Calculate carbon credits potential
            from .carbon_credits import carbon_calculator
            
            species_mapping = {
                'Indigenous Mix': 'Indigenous Mix',
                'Grevillea': 'Grevillea', 
                'Acacia': 'Acacia',
                'Pine': 'Pine',
                'Cedar': 'Cedar',
                'Eucalyptus': 'Eucalyptus',
                'Cypress': 'Cypress',
                'Neem': 'Neem',
                'Wattle': 'Wattle',
                'Bamboo': 'Bamboo'
            }
            
            species = species_mapping.get(tree_data.get('tree_species', 'Indigenous Mix'), 'Indigenous Mix')
            carbon_data = carbon_calculator.calculate_carbon_potential(
                species=species,
                age_months=tree_data.get('tree_age_months', 12),
                survival_rate=int(hybrid_probability * 100),
                location_data={
                    'rainfall_mm': tree_data.get('rainfall_mm', 600),
                    'temperature_c': tree_data.get('temperature_c', 22),
                    'soil_ph': tree_data.get('soil_ph', 6.5)
                }
            )
            
            return {
                'success': True,
                'survival_probability': hybrid_probability,
                'survival_percentage': int(hybrid_probability * 100),
                'risk_level': risk_level,
                'recommendation': recommendation,
                'confidence': confidence,
                'prediction_method': prediction_method,
                'ml_prediction': ml_probability,
                'ai_prediction': ai_probability,
                'model_agreement': agreement if ai_probability else None,
                'carbon_potential': carbon_data
            }
            
        except Exception as e:
            logger.error(f"Hybrid prediction failed: {str(e)}")
            # Fallback to original ML prediction
            return tree_predictor.predict_survival(tree_data)
    
    def generate_hybrid_recommendation(self, tree_data, hybrid_prob, ml_prob, ai_prob):
        """Generate recommendation based on hybrid prediction"""
        
        species = tree_data.get('tree_species', 'tree')
        
        if hybrid_prob >= 0.75:
            base_rec = f"Excellent conditions for {species}. "
        elif hybrid_prob >= 0.6:
            base_rec = f"Good conditions for {species}. "
        elif hybrid_prob >= 0.4:
            base_rec = f"Moderate conditions for {species}. "
        else:
            base_rec = f"Challenging conditions for {species}. "
        
        # Add model agreement insight
        if ai_prob is not None:
            agreement = abs(ml_prob - ai_prob)
            if agreement < 0.1:
                base_rec += "Both ML and AI models strongly agree on this prediction. "
            elif agreement < 0.2:
                base_rec += "ML and AI models show good agreement. "
            else:
                base_rec += "ML and AI models show some variation - consider multiple approaches. "
        
        # Add specific advice based on probability
        if hybrid_prob < 0.6:
            base_rec += "Consider improving soil conditions and planting timing for better results."
        else:
            base_rec += "Proceed with confidence using recommended best practices."
        
        return base_rec

# Initialize global instance
hybrid_predictor = HybridTreePredictor()