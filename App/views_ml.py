from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import re

from App.models import County, CountySpecies, Species, TreePrediction
from .ml_utils import tree_predictor  # your ML model loader


# ============================================================
# STEP 1–3: Get species recommendations + planting playbook
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def get_species_recommendations(request):
    """
    Returns recommended species for a county with planting guide info.
    """
    try:
        data = json.loads(request.body)
        county_name = data.get('county')
        
        county = County.objects.filter(name=county_name).first()
        if not county:
            return JsonResponse({
                "success": False,
                "error": "County not found",
                "species": [],
                "playbook": {}
            })

        county_species_qs = CountySpecies.objects.filter(
            county=county
        ).select_related('species')

        species_list = [cs.species for cs in county_species_qs]

        playbook = {}
        for s in species_list:
            playbook[s.name] = {
                "planting_guide": s.planting_guide,
                "best_month": s.best_season,
                "soil": s.soil,
                "rainfall_mm": s.rainfall,
                "temperature_c": s.temperature,
                "care_instructions": s.care_instructions,
            }

        return JsonResponse({
            "success": True,
            "species": [s.name for s in species_list],
            "playbook": playbook
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
            "species": [],
            "playbook": {}
        })


# ============================================================
# STEP 5–7: Predict tree survival
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def predict_tree_survival(request):
    """
    Predicts survival probability for a species using minimal user input.
    """
    try:
        data = json.loads(request.body)

        # Required input
        tree_species_name = data.get('tree_species')
        county_name = data.get('county')
        planting_season = data.get('planting_season')
        planting_method = data.get('planting_method')
        care_level = data.get('care_level', "Medium")

        # Validate inputs
        if not tree_species_name or not county_name or not planting_season:
            return JsonResponse({"success": False, "error": "Missing required fields"})

        # Get county-species compatibility from database
        try:
            county = County.objects.get(name=county_name)
            species = Species.objects.get(name=tree_species_name)
            county_species = CountySpecies.objects.get(county=county, species=species)
        except County.DoesNotExist:
            return JsonResponse({"success": False, "error": f"County '{county_name}' not found"})
        except Species.DoesNotExist:
            return JsonResponse({"success": False, "error": f"Species '{tree_species_name}' not found"})
        except CountySpecies.DoesNotExist:
            return JsonResponse({"success": False, "error": f"'{tree_species_name}' is not recommended for '{county_name}'"})

        # Get base survival rate from database
        base_survival_rate = county_species.survival_rate
        
        # Check seasonal performance
        seasonal_performance = county_species.seasonal_performance or {}
        seasonal_bonus = 0
        
        # Find matching season
        planting_season_lower = planting_season.lower().replace('–', '-').replace('—', '-')
        
        for season_key, bonus in seasonal_performance.items():
            season_key_lower = season_key.lower().replace('–', '-').replace('—', '-')
            
            # Check if any part of the season matches
            if any(month in planting_season_lower for month in ['march', 'april', 'may', 'june', 'july', 'august', 'september', 'sept', 'october', 'oct', 'november', 'december', 'dec'] if month in season_key_lower):
                seasonal_bonus = bonus
                break
        
        # HYBRID APPROACH: Use ML Model + Playbook Enhancement
        ml_prediction = None
        playbook_prediction = base_survival_rate
        
        # Step 1: Try ML Model first
        try:
            from .ml_utils import tree_predictor
            env = county.environment if hasattr(county, 'environment') else None
            
            if env:
                ml_features = {
                    'county': county_name,
                    'region': getattr(env, 'climate_zone', 'Central'),
                    'rainfall_mm': (env.rainfall_mm_min + env.rainfall_mm_max) / 2,
                    'temperature_c': (env.temperature_c_min + env.temperature_c_max) / 2,
                    'altitude_m': (env.altitude_m_min + env.altitude_m_max) / 2,
                    'soil_ph': 6.5,
                    'soil_type': env.soil_type,
                    'tree_species': tree_species_name,
                    'planting_season': planting_season,
                    'planting_method': planting_method,
                    'care_level': care_level,
                    'water_source': 'Rain-fed',
                    'tree_age_months': 12
                }
            else:
                ml_features = {
                    'county': county_name,
                    'region': 'Central',
                    'rainfall_mm': 800,
                    'temperature_c': 22,
                    'altitude_m': 1500,
                    'soil_ph': 6.5,
                    'soil_type': 'Loam',
                    'tree_species': tree_species_name,
                    'planting_season': planting_season,
                    'planting_method': planting_method,
                    'care_level': care_level,
                    'water_source': 'Rain-fed',
                    'tree_age_months': 12
                }
            
            ml_result = tree_predictor.predict_survival(ml_features)
            if ml_result['success']:
                ml_prediction = ml_result['survival_percentage']
                print(f"   ML Model prediction: {ml_prediction:.1f}%")
            
        except Exception as e:
            print(f"   ML model failed: {e}")
        
        # Step 2: Calculate Playbook-enhanced prediction
        playbook_prediction = base_survival_rate
        
        # Apply seasonal adjustments
        if seasonal_bonus != 0:
            playbook_prediction += seasonal_bonus
        
        # Apply environmental matching from playbook
        env = county.environment if hasattr(county, 'environment') else None
        if env:
            avg_rainfall = (env.rainfall_mm_min + env.rainfall_mm_max) / 2
            if hasattr(species, 'rainfall_optimal_min') and hasattr(species, 'rainfall_optimal_max'):
                if species.rainfall_optimal_min <= avg_rainfall <= species.rainfall_optimal_max:
                    playbook_prediction += 8
                elif avg_rainfall < species.rainfall_optimal_min * 0.7:
                    playbook_prediction -= 15
                elif avg_rainfall > species.rainfall_optimal_max * 1.3:
                    playbook_prediction -= 10
            
            avg_altitude = (env.altitude_m_min + env.altitude_m_max) / 2
            if hasattr(species, 'altitude_preference'):
                if species.altitude_preference == 'Highland' and avg_altitude > 1500:
                    playbook_prediction += 5
                elif species.altitude_preference == 'Lowland' and avg_altitude < 1000:
                    playbook_prediction += 5
                elif species.altitude_preference == 'Highland' and avg_altitude < 800:
                    playbook_prediction -= 12
                elif species.altitude_preference == 'Lowland' and avg_altitude > 2000:
                    playbook_prediction -= 12
        
        care_adjustments = {'High': 8, 'Medium': 0, 'Low': -5}
        playbook_prediction += care_adjustments.get(care_level, 0)
        playbook_prediction = max(15, min(95, playbook_prediction))
        
        print(f"   Playbook prediction: {playbook_prediction:.1f}%")
        
        # Step 3: Combine predictions with improved weighting (trust expert knowledge more)
        if ml_prediction is not None:
            # Use weighted average: 40% ML model + 60% playbook (trust expert knowledge more)
            base_prediction = (ml_prediction * 0.4) + (playbook_prediction * 0.6)
            print(f"   Hybrid prediction (40% ML + 60% Playbook): {base_prediction:.1f}%")
        else:
            # Fallback to playbook only
            base_prediction = playbook_prediction
            print(f"   Using playbook prediction only: {base_prediction:.1f}%")
        
        # Step 4: Add user experience factor
        user_experience_bonus = {'High': 15, 'Medium': 8, 'Low': 0}.get(care_level, 0)
        
        # Step 5: LLM Intelligence Layer - Let LLM analyze and adjust the prediction
        try:
            from .mistral_ai import analyze_prediction_with_llm
            llm_context = {
                'species': tree_species_name,
                'county': county_name,
                'season': planting_season,
                'base_prediction': base_prediction,
                'ml_prediction': ml_prediction,
                'playbook_prediction': playbook_prediction,
                'seasonal_bonus': seasonal_bonus,
                'care_level': care_level,
                'species_data': {
                    'rainfall_optimal': f"{getattr(species, 'rainfall_optimal_min', 600)}-{getattr(species, 'rainfall_optimal_max', 1200)}mm",
                    'altitude_preference': getattr(species, 'altitude_preference', 'Any'),
                    'best_season': species.best_season
                }
            }
            
            llm_adjustment = analyze_prediction_with_llm(llm_context)
            final_survival_rate = base_prediction + user_experience_bonus + llm_adjustment
            print(f"   LLM adjustment: {llm_adjustment:+.1f}%, Experience bonus: {user_experience_bonus:+}%")
            print(f"   Final prediction: {final_survival_rate:.1f}%")
            
        except Exception as e:
            print(f"   LLM analysis failed: {e}")
            final_survival_rate = base_prediction + user_experience_bonus
            print(f"   Final prediction (no LLM): {final_survival_rate:.1f}%")
        
        final_survival_rate = max(20, min(95, final_survival_rate))
        
        # Convert to probability
        survival_probability = final_survival_rate / 100.0
        
        # Determine risk level with updated thresholds
        if final_survival_rate >= 80:
            risk_level = "Low"
        elif final_survival_rate >= 65:
            risk_level = "Medium"
        elif final_survival_rate >= 45:
            risk_level = "High"
        else:
            risk_level = "Very High"

        print(f"[PREDICTION] {county_name} -> {tree_species_name}")
        print(f"   Survival rate: {final_survival_rate}% ({risk_level} risk)")
        print(f"   Reason: {county_species.recommendation_reason}")
        print(f"   Season: {planting_season} (bonus: {seasonal_bonus:+}%)")

        # Generate intelligent explanation that matches the prediction
        try:
            from .mistral_ai import generate_tree_explanation
            llm_context = {
                'species': tree_species_name,
                'county': county_name,
                'season': planting_season,
                'survival_rate': final_survival_rate,
                'risk_level': risk_level,
                'reason': county_species.recommendation_reason,
                'seasonal_bonus': seasonal_bonus,
                'best_season': species.best_season
            }
            explanation = generate_tree_explanation(llm_context)
            print(f"   Enhanced explanation generated")
        except Exception as e:
            print(f"   Using enhanced fallback explanation")
            # Enhanced fallback that matches the prediction
            if final_survival_rate >= 75:
                explanation = f"{tree_species_name} performs excellently in {county_name}. {county_species.recommendation_reason}. Your timing in {planting_season} provides optimal growing conditions."
            elif final_survival_rate >= 60:
                explanation = f"{tree_species_name} shows good potential in {county_name}. {county_species.recommendation_reason}. Planting in {planting_season} is suitable with proper care."
            elif final_survival_rate >= 40:
                explanation = f"{tree_species_name} faces some challenges in {county_name} during {planting_season}. While {county_species.recommendation_reason.lower()}, current conditions require extra attention."
            else:
                explanation = f"{tree_species_name} encounters significant challenges in {county_name} during {planting_season}. Though {county_species.recommendation_reason.lower()}, current timing and conditions are not optimal."
        
        # Generate intelligent care instructions that match the risk level
        try:
            from .mistral_ai import generate_care_instructions
            care_context = {
                'species': tree_species_name,
                'county': county_name,
                'season': planting_season,
                'survival_rate': final_survival_rate,
                'risk_level': risk_level,
                'base_care': species.care_instructions or []
            }
            after_care = generate_care_instructions(care_context)
            print(f"   Enhanced care instructions generated")
        except Exception as e:
            print(f"   Using enhanced care instructions")
            # Enhanced care instructions based on risk level
            if final_survival_rate >= 80:  # Low risk - standard care
                after_care = species.care_instructions or ["Follow standard tree care practices"]
            elif final_survival_rate >= 65:  # Medium risk - enhanced care
                if "Follow the care instructions closely" not in explanation:
                    explanation += f" Follow the care instructions closely to maximize success."
                after_care = species.care_instructions or ["Follow standard tree care practices"]
            else:  # High/Very High risk - alternatives or wait
                # Find alternative species that work well in this season for this county
                alternative_species = CountySpecies.objects.filter(
                    county=county,
                    survival_rate__gte=70
                ).exclude(species=species).select_related('species')
                
                # Check which alternatives have good seasonal performance for current season
                good_alternatives = []
                for alt_cs in alternative_species:
                    alt_seasonal = alt_cs.seasonal_performance or {}
                    alt_bonus = 0
                    for season_key, bonus in alt_seasonal.items():
                        if any(month in planting_season_lower for month in ['march', 'april', 'may', 'june', 'july', 'august', 'september', 'sept', 'october', 'oct', 'november', 'december', 'dec'] if month in season_key.lower()):
                            alt_bonus = bonus
                            break
                    # Only consider species with significantly better survival rates (avoid circular recommendations)
                    if alt_bonus >= 0 and alt_cs.survival_rate > final_survival_rate + 15:  # Must be 15% better
                        good_alternatives.append(alt_cs.species.name)
                
                if good_alternatives:
                    best_alternative = good_alternatives[0]
                    if "For better results" not in explanation:
                        explanation += f" For significantly better results in {planting_season}, try {best_alternative} which has higher success rates during this season."
                    # Get alternative species care instructions
                    alt_species = Species.objects.get(name=best_alternative)
                    after_care = [f"Recommended: Plant {best_alternative} instead (better survival rate)"] + (alt_species.care_instructions or [])
                else:
                    if "For better results" not in explanation:
                        explanation += f" For better results, wait for the optimal planting season ({species.best_season}) when conditions are more favorable."
                    after_care = [f"Recommended: Wait for {species.best_season} for optimal conditions", "Prepare planting site with compost and proper drainage", "Source quality seedlings before the season", "Consider soil testing and improvement"]

        # Save prediction (if logged in)
        if hasattr(request, 'user') and request.user.is_authenticated:
            TreePrediction.objects.create(
                user=request.user,
                tree_species=tree_species_name,
                county=county_name,
                region=getattr(county, 'environment', None) and county.environment.climate_zone or 'Unknown',
                soil_type=species.soil,
                rainfall_mm=0,  # Will be enhanced later
                temperature_c=0,  # Will be enhanced later
                altitude_m=0,  # Will be enhanced later
                soil_ph=0,  # Will be enhanced later
                planting_season=planting_season,
                planting_method=planting_method,
                care_level=care_level,
                water_source="Unknown",
                tree_age_months=0,
                survival_probability=survival_probability,
                survival_level=risk_level.lower()
            )

        return JsonResponse({
            "success": True,
            "survival_percentage": round(final_survival_rate, 1),
            "risk_level": risk_level,
            "after_care": after_care,
            "explanation": explanation,
            "species_rank": county_species.species_rank,
            "match_score": county_species.environmental_match_score,
            "recommendation_reason": county_species.recommendation_reason,
            "alternative_species": good_alternatives[:2] if 'good_alternatives' in locals() else [],
            "prediction_sources": {
                "ml_prediction": ml_prediction,
                "playbook_prediction": playbook_prediction,
                "experience_bonus": user_experience_bonus,
                "final_prediction": round(final_survival_rate, 1)
            },
            "alternative_species": good_alternatives[:2] if 'good_alternatives' in locals() else []
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ============================================================
# STEP 4: Get environment data from county
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def get_county_environment(request):
    try:
        data = json.loads(request.body)
        county_name = data.get('county')

        county = County.objects.filter(name=county_name).first()
        if not county or not hasattr(county, "environment"):
            return JsonResponse({
                "success": False,
                "error": "County environment not found",
                "environment": {}
            })

        env = county.environment

        return JsonResponse({
            "success": True,
            "environment": {
                "altitude_m": (env.altitude_m_min + env.altitude_m_max) / 2,
                "rainfall_mm": (env.rainfall_mm_min + env.rainfall_mm_max) / 2,
                "temperature_c": (env.temperature_c_min + env.temperature_c_max) / 2,
                "soil_type": env.soil_type,
                "best_season": env.best_season,
            }
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "environment": {}})
