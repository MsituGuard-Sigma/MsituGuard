"""
LLM integration for Tree Prediction explanations and care instructions
"""
import os
try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    try:
        from mistralai import Mistral
        MistralClient = Mistral
        class ChatMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
    except ImportError:
        MistralClient = None
        ChatMessage = None

# Initialize Mistral client
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.environ.get("MISTRAL_API_KEY")
client = MistralClient(api_key=api_key) if api_key else None

print(f"[MISTRAL] API Key configured: {'Yes' if api_key else 'No'}")
print(f"[MISTRAL] Client initialized: {'Yes' if client else 'No'}")

def generate_tree_explanation(context):
    """Generate natural explanation for tree prediction using LLM"""
    if not client:
        print("[MISTRAL] No client available, using fallback explanation")
        # Fallback to enhanced static explanation when no API key
        species = context['species']
        county = context['county']
        season = context['season']
        survival_rate = context['survival_rate']
        reason = context['reason']
        
        if survival_rate >= 80:
            return f"{species} grows excellently in {county}'s environmental conditions. {reason}. Your chosen season ({season}) provides optimal growing conditions with good rainfall and temperature."
        elif survival_rate >= 65:
            return f"{species} performs well in {county} with proper care. {reason}. Planting in {season} is suitable, though following care instructions closely will maximize success."
        else:
            return f"{species} faces challenges in {county} during {season}. {reason}. Consider alternative species or wait for optimal planting season for better results."
    
    prompt = f"""
    You are an expert Kenyan forestry advisor. Generate a clear, simple explanation for this tree planting prediction:

    Species: {context['species']}
    Location: {context['county']} County, Kenya
    Planting Season: {context['season']}
    Survival Rate: {context['survival_rate']:.1f}%
    Risk Level: {context['risk_level']}
    
    Base reason: {context['reason']}
    
    Instructions:
    - Explain WHY this species works well (or doesn't) in this location and season
    - Use simple, practical language that farmers understand
    - Focus on environmental factors (rainfall, soil, temperature)
    - Keep it under 80 words
    - Don't mention percentages, technical terms, or word counts
    - Be encouraging but honest
    - Don't use markdown formatting or quotes
    - Write in plain text only
    
    Example style: "Pine grows well in Meru's highland climate with good rainfall. March planting is ideal because it coincides with long rains when trees establish strong roots."
    """
    
    messages = [ChatMessage(role="user", content=prompt)]
    
    try:
        if hasattr(client, 'chat'):
            response = client.chat(
                model="mistral-small",
                messages=messages,
                max_tokens=150,
                temperature=0.3
            )
        else:
            # Try newer API format
            response = client.completions.create(
                model="mistral-small",
                messages=messages,
                max_tokens=150,
                temperature=0.3
            )
        # Clean up LLM response
        content = response.choices[0].message.content.strip()
        # Remove markdown formatting, quotes, and word count
        content = content.replace('**', '').replace('*', '')
        content = content.replace('"', '').replace("'", "")
        # Remove word count pattern
        import re
        content = re.sub(r'\(Word count:.*?\)', '', content)
        content = re.sub(r'\(\d+\s*words?\)', '', content)
        return content.strip()
    except Exception as e:
        raise Exception(f"LLM explanation failed: {str(e)}")

def generate_care_instructions(context):
    """Generate personalized care instructions using LLM"""
    if not client:
        print("[MISTRAL] No client available, using fallback care instructions")
        # Fallback to enhanced care instructions when no API key
        base_care = context.get('base_care', [])
        survival_rate = context['survival_rate']
        risk_level = context['risk_level']
        
        if survival_rate >= 80:  # Low risk
            return base_care or ["Water regularly for first month", "Apply mulch around base", "Protect from livestock", "Monitor for pests monthly"]
        elif survival_rate >= 65:  # Medium risk
            enhanced_care = ["CRITICAL: Follow all care steps closely"] + (base_care or [])
            enhanced_care.append("Check soil moisture weekly")
            return enhanced_care[:6]
        else:  # High risk
            return ["Consider alternative species for this season", "If proceeding: water daily for first 2 months", "Apply organic fertilizer monthly", "Provide shade during hot periods", "Monitor daily for stress signs"]
    
    base_care = context.get('base_care', [])
    base_care_text = "; ".join(base_care) if base_care else "Standard tree care"
    
    prompt = f"""
    You are an expert Kenyan forestry advisor. Generate personalized care instructions for this tree planting:

    Species: {context['species']}
    Location: {context['county']} County, Kenya
    Planting Season: {context['season']}
    Survival Rate: {context['survival_rate']:.1f}%
    Risk Level: {context['risk_level']}
    
    Base care instructions: {base_care_text}
    
    Instructions:
    - Adapt the care instructions for the specific survival rate and risk level
    - For high risk (low survival): emphasize critical care steps
    - For medium risk: add extra precautions
    - For low risk: provide standard care with confidence
    - Use practical, actionable language
    - Consider Kenyan farming conditions and resources
    - Return as a list of 4-6 specific care steps
    - Each step should be one clear, complete sentence
    - Don't use markdown formatting or quotes
    - Write in plain text only
    - Keep each instruction under 100 characters
    """
    
    messages = [ChatMessage(role="user", content=prompt)]
    
    try:
        response = client.chat(
            model="mistral-small",
            messages=messages,
            max_tokens=200,
            temperature=0.3
        )
        
        # Parse response into list
        care_text = response.choices[0].message.content.strip()
        care_lines = [line.strip() for line in care_text.split('\n') if line.strip()]
        
        # Clean up numbered items
        care_instructions = []
        for line in care_lines:
            # Remove numbers and clean up
            cleaned = line.lstrip('0123456789.- ').strip()
            if cleaned and len(cleaned) > 10:  # Valid instruction
                care_instructions.append(cleaned)
        
        # Clean up care instructions
        cleaned_instructions = []
        for instruction in care_instructions[:6]:
            # Remove markdown and formatting
            clean = instruction.replace('**', '').replace('*', '')
            clean = clean.replace('"', '').replace("'", "")
            # Remove incomplete sentences (ending with incomplete words)
            if len(clean) > 20 and not clean.endswith(('with', 'using', 'to', 'for', 'and', 'or')):
                cleaned_instructions.append(clean)
        
        return cleaned_instructions if cleaned_instructions else base_care
        
    except Exception as e:
        raise Exception(f"LLM care instructions failed: {str(e)}")

def analyze_prediction_with_llm(context):
    """Use LLM to analyze and adjust prediction based on multiple factors"""
    if not client:
        print("[MISTRAL] No client available, using fallback analysis")
        # Fallback intelligent analysis when no API key
        species = context['species']
        county = context['county']
        seasonal_bonus = context['seasonal_bonus']
        
        # Simple rule-based adjustments
        adjustment = 0
        
        # Seasonal optimization
        if seasonal_bonus > 5:
            adjustment += 5
        elif seasonal_bonus < -5:
            adjustment -= 3
        
        # Enhanced species-specific knowledge for better differentiation
        if species == 'Indigenous Mix' and county in ['Meru', 'Nyeri', 'Kiambu']:
            adjustment += 12  # Perfect match - native highland species
        elif species in ['Pine', 'Cypress'] and county in ['Meru', 'Nyeri', 'Kiambu']:
            adjustment += 8   # Excellent match - highland species in highland areas
        elif species == 'Neem' and county in ['Mombasa', 'Kilifi', 'Garissa', 'Turkana']:
            adjustment += 10  # Excellent match - drought tolerant in dry areas
        elif species == 'Eucalyptus':  # Adaptable species
            adjustment += 3   # Good anywhere but not exceptional
        elif species in ['Pine', 'Cypress'] and county in ['Mombasa', 'Kilifi']:
            adjustment -= 12  # Poor match - highland species in coastal areas
        elif species == 'Neem' and county in ['Meru', 'Nyeri']:
            adjustment -= 8   # Poor match - lowland species in highland areas
        
        return max(-15, min(12, adjustment))
    
    # LLM analysis would go here
    return 0