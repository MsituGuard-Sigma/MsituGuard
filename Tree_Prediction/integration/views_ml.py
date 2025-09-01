from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .ml_utils import tree_predictor
from App.models import TreePrediction
from App.mistral_ai import mistral_ai
from App.hybrid_predictor import hybrid_predictor



@csrf_exempt
@require_http_methods(["POST"])
def predict_tree_survival(request):
    """API endpoint for tree survival prediction"""
    
    try:
        data = json.loads(request.body)
        
        # Extract required fields
        tree_data = {
            'tree_species': data.get('tree_species', 'Eucalyptus'),
            'region': data.get('region', 'Central'),
            'county': data.get('county', 'Nairobi'),
            'soil_type': data.get('soil_type', 'Loam'),
            'rainfall_mm': float(data.get('rainfall_mm', 600)),
            'temperature_c': float(data.get('temperature_c', 20)),
            'altitude_m': float(data.get('altitude_m', 1500)),
            'soil_ph': float(data.get('soil_ph', 6.5)),
            'planting_season': data.get('planting_season', 'Wet'),
            'planting_method': data.get('planting_method', 'Seedling'),
            'care_level': data.get('care_level', 'Medium'),
            'water_source': data.get('water_source', 'Rain-fed'),
            'tree_age_months': int(data.get('tree_age_months', 12))
        }
        
        # Get hybrid prediction (ML + AI)
        result = hybrid_predictor.hybrid_predict(tree_data)
        
        # Save prediction to database for logged-in users
        if request.user.is_authenticated and result.get('success', False):
            # Determine survival level based on probability
            prob = result.get('survival_probability', 0)
            if prob >= 0.7:
                survival_level = 'high'
            elif prob >= 0.5:
                survival_level = 'medium'
            else:
                survival_level = 'low'
            
            TreePrediction.objects.create(
                user=request.user,
                tree_species=tree_data['tree_species'],
                region=tree_data['region'],
                county=tree_data['county'],
                soil_type=tree_data['soil_type'],
                rainfall_mm=tree_data['rainfall_mm'],
                temperature_c=tree_data['temperature_c'],
                altitude_m=tree_data['altitude_m'],
                soil_ph=tree_data['soil_ph'],
                planting_season=tree_data['planting_season'],
                planting_method=tree_data['planting_method'],
                care_level=tree_data['care_level'],
                water_source=tree_data['water_source'],
                tree_age_months=tree_data['tree_age_months'],
                survival_probability=prob,
                survival_level=survival_level,
                recommended_species=json.dumps(result.get('recommended_species', []))
            )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'survival_probability': 0.5,
            'recommendation': 'Error in prediction'
        })

@csrf_exempt
@require_http_methods(["POST"])
def get_species_recommendations(request):
    """API endpoint for species recommendations based on location - requires login"""
    
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Login required for species recommendations',
                'login_required': True,
                'recommendations': []
            })
        
        data = json.loads(request.body)
        
        location_data = {
            'region': data.get('region', 'Central'),
            'county': data.get('county', 'Nairobi'),
            'soil_type': data.get('soil_type', 'Loam'),
            'rainfall_mm': float(data.get('rainfall_mm', 600)),
            'temperature_c': float(data.get('temperature_c', 20)),
            'altitude_m': float(data.get('altitude_m', 1500)),
            'soil_ph': float(data.get('soil_ph', 6.5)),
            'planting_season': data.get('planting_season', 'Wet'),
            'water_source': data.get('water_source', 'Rain-fed'),
            'tree_species': data.get('tree_species', 'Acacia')
        }
        
        # Get ML-based recommendations
        recommendations = tree_predictor.get_species_recommendations(location_data)
        
        # Get current species survival rate for AI context
        current_prediction = tree_predictor.predict_survival(location_data)
        survival_rate = int(current_prediction.get('survival_probability', 0.5) * 100)
        
        # Enhance with MISTRAL AI recommendations (with fallback)
        try:
            print(f"Calling MISTRAL AI with API key available: {bool(mistral_ai.api_key)}")
            ai_recommendations = mistral_ai.get_tree_recommendations(location_data, survival_rate)
            ai_species = mistral_ai.get_alternative_species(location_data)
            ai_explanation = mistral_ai.explain_prediction_factors(location_data, survival_rate)
            print(f"MISTRAL AI responses - recommendations: {len(ai_recommendations) if ai_recommendations else 0} chars")
        except Exception as e:
            print(f"MISTRAL AI error in species recommendations: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            # Fallback recommendations
            ai_recommendations = "Unable to generate recommendations."
            ai_species = "Unable to generate species suggestions."
            ai_explanation = "Unable to generate analysis."
        
        print(f"Final response - ai_recommendations: {ai_recommendations[:100]}...")
        print(f"Final response - ai_species: {ai_species[:100]}...")
        print(f"Final response - ai_explanation: {ai_explanation[:100]}...")
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations,
            'ai_recommendations': ai_recommendations,
            'ai_species_suggestions': ai_species,
            'ai_explanation': ai_explanation
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'recommendations': []
        })

@csrf_exempt
@require_http_methods(["POST"])
def get_climate_data(request):
    """API endpoint to get climate data from GPS coordinates using real dataset"""
    
    try:
        data = json.loads(request.body)
        
        latitude = float(data.get('latitude', -1.2921))
        longitude = float(data.get('longitude', 36.8219))
        altitude = data.get('altitude')
        
        # Get climate data using real dataset averages
        location_data = tree_predictor.get_climate_from_gps(latitude, longitude, altitude)
        
        return JsonResponse({
            'success': True,
            'location_data': location_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'location_data': {}
        })