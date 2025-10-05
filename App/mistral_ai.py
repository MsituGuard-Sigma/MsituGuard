import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class MistralAI:
    def __init__(self):
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
        
    @property
    def api_key(self):
        """Get API key dynamically from settings"""
        return getattr(settings, 'MISTRAL_API_KEY', None)
        
    def _make_request(self, messages, max_tokens=300):
        """Make request to MISTRAL API"""
        if not self.api_key:
            logger.warning("MISTRAL API key not configured")
            return None
            
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-tiny",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # Remove common AI response prefixes
                prefixes_to_remove = [
                    "Sure, I'd be happy to explain!",
                    "Sure, I'd be happy to help!",
                    "I'd be happy to explain!",
                    "I'd be happy to help!",
                    "Certainly!",
                    "Of course!"
                ]
                
                for prefix in prefixes_to_remove:
                    if content.startswith(prefix):
                        content = content[len(prefix):].strip()
                        break
                
                return content
            elif response.status_code == 401:
                logger.error("MISTRAL API: Invalid API key")
                return None
            elif response.status_code == 429:
                logger.error("MISTRAL API: Rate limit exceeded")
                time.sleep(1)  # Brief pause for rate limiting
                return None
            else:
                logger.error(f"MISTRAL API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("MISTRAL API request timed out")
            return None
        except Exception as e:
            logger.error(f"MISTRAL API request failed: {str(e)}")
            return None
    
    def get_tree_recommendations(self, prediction_data, survival_rate):
        """Generate AI-powered tree planting recommendations"""
        
        if not self.api_key:
            return "Unable to generate recommendations."
        
        system_prompt = """You are a Kenyan forestry expert AI. Provide practical, actionable tree planting advice based on environmental data and survival predictions. Focus on specific, implementable recommendations."""
        
        user_prompt = f"""
        {prediction_data.get('tree_species', 'Tree')} in {prediction_data.get('county', 'Kenya')} - {survival_rate}% survival rate.
        
        Conditions: {prediction_data.get('soil_type', 'Unknown')} soil, {prediction_data.get('rainfall_mm', 'Unknown')}mm rain, {prediction_data.get('temperature_c', 'Unknown')}°C.
        
        Give 3 specific tips to improve survival:
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self._make_request(messages, max_tokens=200)
        if result and len(result.strip()) > 10:
            return result
        return f"1. Plant during wet season for better water availability\n2. Improve soil drainage and add organic matter\n3. Use seedlings instead of direct seeding for {prediction_data.get('tree_species', 'trees')}"
    
    def get_alternative_species(self, prediction_data):
        """Get AI-recommended alternative tree species"""
        
        if not self.api_key:
            return "Unable to generate species suggestions."
        
        system_prompt = """You are a Kenyan forestry expert. Recommend native Kenyan tree species that would thrive in the given environmental conditions. Focus on indigenous and well-adapted species."""
        
        user_prompt = f"""
        {prediction_data.get('county', 'Kenya')} conditions: {prediction_data.get('soil_type', 'Unknown')} soil, {prediction_data.get('rainfall_mm', 'Unknown')}mm rain, {prediction_data.get('temperature_c', 'Unknown')}°C.
        
        List 4 best Kenyan tree species for these conditions:
        Format: "Species - Survival% - Benefit"
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self._make_request(messages, max_tokens=150)
        if result and len(result.strip()) > 10:
            return result
        # Provide region-specific fallback
        region = prediction_data.get('region', 'Central')
        if region in ['Coast', 'Eastern']:
            return "Casuarina - 88% - Salt tolerant\nNeem - 82% - Drought resistant\nAcacia - 78% - Hardy species\nBaobab - 75% - Water storage"
        elif region in ['Western', 'Nyanza']:
            return "Indigenous Mix - 90% - Well adapted\nGrevillea - 87% - Fast growing\nPine - 80% - High altitude\nCypress - 78% - Moisture loving"
        else:
            return "Indigenous Mix - 85% - Well adapted\nGrevillea - 80% - Fast growing\nAcacia - 75% - Drought resistant\nCedar - 72% - Premium timber"
    
    def explain_prediction_factors(self, prediction_data, survival_rate):
        """Explain why certain factors affect the prediction"""
        
        if not self.api_key:
            return "Unable to generate analysis."
        
        system_prompt = """You are a Kenyan forestry expert AI. Explain in simple terms why environmental factors affect tree survival rates. Be educational and easy to understand."""
        
        user_prompt = f"""
        Explain why this tree planting scenario has a {survival_rate}% survival rate:
        
        Species: {prediction_data.get('tree_species', 'Unknown')}
        Location: {prediction_data.get('county', 'Unknown')}, {prediction_data.get('region', 'Unknown')}
        Soil: {prediction_data.get('soil_type', 'Unknown')} (pH {prediction_data.get('soil_ph', 'Unknown')})
        Rainfall: {prediction_data.get('rainfall_mm', 'Unknown')}mm/year
        Temperature: {prediction_data.get('temperature_c', 'Unknown')}°C
        
        Explain in 2-3 sentences what factors are helping or hindering tree survival in this scenario.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self._make_request(messages, max_tokens=150)
        return result if result else "Environmental factors affect tree survival based on species adaptation to local conditions."

# Initialize global instance
mistral_ai = MistralAI()