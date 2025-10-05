"""
Carbon Credits System for MsituGuard
Calculates CO2 absorption and carbon credit potential for trees
"""

from .mistral_ai import mistral_ai
import logging

logger = logging.getLogger(__name__)

class CarbonCreditsCalculator:
    """Calculate carbon credits for trees based on species, age, and environmental factors"""
    
    # CO2 absorption rates by species (kg CO2/year when mature)
    SPECIES_CO2_RATES = {
        'Indigenous Mix': 25,
        'Grevillea': 20,
        'Acacia': 18,
        'Pine': 30,
        'Cedar': 28,
        'Eucalyptus': 22,
        'Cypress': 24,
        'Neem': 19,
        'Wattle': 16,
        'Bamboo': 35,  # High CO2 absorption
        'Casuarina': 21,
        'Jacaranda': 17,
    }
    
    # Carbon credit market price (KES per tonne CO2)
    CARBON_PRICE_KES = 500  # ~$5 USD per tonne
    
    def calculate_carbon_potential(self, species, age_months, survival_rate=100, location_data=None):
        """Calculate carbon absorption and credit potential"""
        
        # Get base CO2 rate for species
        base_co2 = self.SPECIES_CO2_RATES.get(species, 22)
        
        # Age factor (trees absorb more as they grow)
        age_factor = self._get_age_factor(age_months)
        
        # Environmental factor based on location
        env_factor = self._get_environmental_factor(location_data) if location_data else 1.0
        
        # Calculate annual CO2 absorption
        annual_co2_kg = base_co2 * age_factor * env_factor * (survival_rate / 100)
        
        # Convert to tonnes for carbon credits
        annual_co2_tonnes = annual_co2_kg / 1000
        
        # Calculate potential earnings
        annual_value_kes = annual_co2_tonnes * self.CARBON_PRICE_KES
        
        return {
            'annual_co2_kg': round(annual_co2_kg, 1),
            'annual_co2_tonnes': round(annual_co2_tonnes, 3),
            'annual_value_kes': round(annual_value_kes, 2),
            'carbon_credits_per_year': round(annual_co2_tonnes, 3),
            'age_factor': age_factor,
            'maturity_status': self._get_maturity_status(age_months),
            'earning_timeline': self._get_earning_timeline(age_months)
        }
    
    def _get_age_factor(self, age_months):
        """Calculate CO2 absorption factor based on tree age"""
        if age_months < 6:
            return 0.05  # 5% of mature rate (seedlings)
        elif age_months < 12:
            return 0.15  # 15% of mature rate
        elif age_months < 24:
            return 0.35  # 35% of mature rate
        elif age_months < 36:
            return 0.65  # 65% of mature rate
        elif age_months < 48:
            return 0.85  # 85% of mature rate
        else:
            return 1.0   # Full mature rate (4+ years)
    
    def _get_environmental_factor(self, location_data):
        """Adjust CO2 absorption based on environmental conditions"""
        if not location_data:
            return 1.0
        
        factor = 1.0
        
        # Rainfall factor
        rainfall = location_data.get('rainfall_mm', 800)
        if rainfall < 500:
            factor *= 0.7  # Drought stress
        elif rainfall < 700:
            factor *= 0.85
        elif rainfall > 1200:
            factor *= 1.1  # Optimal conditions
        
        # Temperature factor
        temp = location_data.get('temperature_c', 22)
        if temp < 15 or temp > 30:
            factor *= 0.9  # Stress conditions
        
        # Soil pH factor
        ph = location_data.get('soil_ph', 6.5)
        if 6.0 <= ph <= 7.0:
            factor *= 1.05  # Optimal pH
        elif ph < 5.5 or ph > 8.0:
            factor *= 0.85  # Poor pH
        
        return min(factor, 1.3)  # Cap at 30% bonus
    
    def _get_maturity_status(self, age_months):
        """Get tree maturity status"""
        if age_months < 12:
            return "Growing"
        elif age_months < 36:
            return "Developing"
        else:
            return "Mature"
    
    def _get_earning_timeline(self, age_months):
        """Get timeline for carbon earning potential"""
        if age_months < 12:
            months_to_earning = 24 - age_months
            return f"Starts earning in {months_to_earning} months"
        elif age_months < 24:
            return "Starting to earn carbon credits"
        else:
            return "Earning carbon credits now"
    
    def calculate_portfolio_value(self, trees_data):
        """Calculate total carbon value for user's tree portfolio"""
        total_co2_kg = 0
        total_value_kes = 0
        growing_trees = 0
        earning_trees = 0
        
        for tree in trees_data:
            carbon_data = self.calculate_carbon_potential(
                tree['species'],
                tree['age_months'],
                tree.get('survival_rate', 100),
                tree.get('location_data')
            )
            
            total_co2_kg += carbon_data['annual_co2_kg']
            total_value_kes += carbon_data['annual_value_kes']
            
            if tree['age_months'] < 24:
                growing_trees += 1
            else:
                earning_trees += 1
        
        return {
            'total_trees': len(trees_data),
            'growing_trees': growing_trees,
            'earning_trees': earning_trees,
            'total_co2_kg_per_year': round(total_co2_kg, 1),
            'total_co2_tonnes_per_year': round(total_co2_kg / 1000, 3),
            'total_value_kes_per_year': round(total_value_kes, 2),
            'average_co2_per_tree': round(total_co2_kg / len(trees_data), 1) if trees_data else 0
        }
    
    def get_ai_carbon_advice(self, tree_data, current_carbon):
        """Get MISTRAL AI advice for maximizing carbon credits"""
        if not mistral_ai.api_key:
            return "AI carbon advisor temporarily unavailable"
        
        try:
            prompt = f"""
            As a carbon credit expert for Kenya, provide 3 specific recommendations to maximize carbon credits for this tree:
            
            Species: {tree_data.get('species', 'Unknown')}
            Age: {tree_data.get('age_months', 0)} months
            Location: {tree_data.get('location', 'Unknown')}
            Current CO2: {current_carbon}kg/year
            
            Provide practical, actionable advice for Kenyan farmers. Keep it concise and specific.
            """
            
            response = mistral_ai._make_request([
                {"role": "system", "content": "You are a carbon credit expert specializing in Kenyan forestry."},
                {"role": "user", "content": prompt}
            ], max_tokens=200)
            
            return response or "Unable to generate carbon advice at this time"
            
        except Exception as e:
            logger.error(f"AI carbon advice error: {e}")
            return "AI carbon advisor temporarily unavailable"
    
    def get_market_insights(self, portfolio_data):
        """Get AI-powered carbon market insights"""
        if not mistral_ai.api_key:
            return "Market insights temporarily unavailable"
        
        try:
            prompt = f"""
            Provide carbon market insights for this portfolio in Kenya:
            
            Total trees: {portfolio_data.get('total_trees', 0)}
            Annual CO2: {portfolio_data.get('total_co2_kg_per_year', 0)}kg
            Current value: {portfolio_data.get('total_value_kes_per_year', 0)} KES
            
            Give brief market timing and pricing insights for Kenyan carbon credits.
            """
            
            response = mistral_ai._make_request([
                {"role": "system", "content": "You are a carbon market analyst for East Africa."},
                {"role": "user", "content": prompt}
            ], max_tokens=150)
            
            return response or "Market insights temporarily unavailable"
            
        except Exception as e:
            logger.error(f"Market insights error: {e}")
            return "Market insights temporarily unavailable"

# Global instance
carbon_calculator = CarbonCreditsCalculator()