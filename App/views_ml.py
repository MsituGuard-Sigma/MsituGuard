from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import re
from django.db import IntegrityError

from App.models import County, CountySpecies, Species, TreePrediction
from .ml_utils import tree_predictor  # your ML model loader


def _normalize_county_name(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    cleaned = re.sub(r"\s+county\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _ensure_default_species():
    """Ensure a small set of baseline species exists for fallback flows."""
    defaults_by_name = {
        "Indigenous Mix": {
            "soil": "Various",
            "rainfall": "600-1200mm",
            "temperature": "15-30°C",
            "care_level": "Low",
            "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling",
            "water": "Low to moderate",
            "planting_guide": ["Dig hole", "Add compost", "Plant seedling", "Mulch"],
            "care_instructions": ["Weed regularly", "Mulch base", "Protect from livestock"],
        },
        "Grevillea": {
            "soil": "Well-drained",
            "rainfall": "600-1000mm",
            "temperature": "15-28°C",
            "care_level": "Low",
            "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling",
            "water": "Low to moderate",
            "planting_guide": ["Plant in open area", "Space trees", "Water initially"],
            "care_instructions": ["Minimal maintenance", "Prune lightly", "Monitor pests"],
        },
        "Neem": {
            "soil": "Sandy to clay",
            "rainfall": "400-1200mm",
            "temperature": "20-35°C",
            "care_level": "Low",
            "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling",
            "water": "Low",
            "planting_guide": ["Plant in warm area", "Water weekly first month", "Mulch"],
            "care_instructions": ["Drought tolerant", "Prune for shape", "Minimal inputs"],
        },
        "Eucalyptus": {
            "soil": "Well-drained",
            "rainfall": "600-1200mm",
            "temperature": "15-25°C",
            "care_level": "Medium",
            "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling",
            "water": "Moderate",
            "planting_guide": ["Plant seedlings", "Space 3-4m", "Water first 6 months"],
            "care_instructions": ["Monitor pests", "Prune lower branches"],
        },
    }

    species_objects = []
    for name, defaults in defaults_by_name.items():
        obj, _ = Species.objects.get_or_create(name=name, defaults=defaults)
        species_objects.append(obj)
    return species_objects


def _ensure_default_county_species(county: County):
    """Ensure the county has at least some CountySpecies mappings."""
    existing = CountySpecies.objects.filter(county=county)
    if existing.exists():
        return

    species_objects = list(Species.objects.all()[:8])
    if not species_objects:
        species_objects = _ensure_default_species()

    for idx, sp in enumerate(species_objects, start=1):
        CountySpecies.objects.get_or_create(
            county=county,
            species=sp,
            defaults={
                "survival_rate": 70.0,
                "species_rank": idx,
                "environmental_match_score": 70.0,
                "seasonal_performance": {},
                "recommendation_reason": "Baseline recommendation (no county-specific playbook loaded yet).",
            },
        )


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
        county_name = _normalize_county_name(data.get('county'))
        if not county_name:
            return JsonResponse({
                "success": False,
                "error": "Missing county",
                "species": [],
                "playbook": {}
            })

        county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            # If DB seeding hasn't happened yet in production, create the county
            # so the UX can still proceed.
            try:
                county = County.objects.create(name=county_name)
            except IntegrityError:
                county = County.objects.filter(name__iexact=county_name).first()

        if not county:
            return JsonResponse({
                "success": False,
                "error": "County not found",
                "species": [],
                "playbook": {}
            })

        # Ensure we can return something even if CountySpecies isn't populated.
        _ensure_default_county_species(county)

        county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')

        species_list = [cs.species for cs in county_species_qs]

        playbook = {}
        for s in species_list:
            playbook[s.name] = {
                "planting_guide": s.planting_guide,
                "best_month": s.best_season,
                "planting_method": getattr(s, "planting_method", "Seedling"),
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
        tree_species_name = (data.get('tree_species') or "").strip()
        county_name = _normalize_county_name(data.get('county'))
        planting_season = data.get('planting_season')
        planting_method = data.get('planting_method')
        care_level = data.get('care_level', "Medium")

        # Validate inputs
        if not tree_species_name or not county_name or not planting_season:
            return JsonResponse({"success": False, "error": "Missing required fields"})

        # Get county-species compatibility from database
        county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            # Allow predictions even if counties were not seeded.
            try:
                county = County.objects.create(name=county_name)
            except IntegrityError:
                county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            return JsonResponse({"success": False, "error": f"County '{county_name}' not found"})

        species = Species.objects.filter(name__iexact=tree_species_name).first()
        if not species:
            # Bootstrap a baseline set if DB wasn't seeded.
            _ensure_default_species()
            species = Species.objects.filter(name__iexact=tree_species_name).first()
        if not species:
            return JsonResponse({"success": False, "error": f"Species '{tree_species_name}' not found"})

        county_species = CountySpecies.objects.filter(county=county, species=species).first()
        if not county_species:
            # Create a baseline mapping so predictions can proceed.
            _ensure_default_county_species(county)
            county_species = CountySpecies.objects.filter(county=county, species=species).first()
        if not county_species:
            return JsonResponse({"success": False, "error": f"'{tree_species_name}' is not available for '{county_name}' yet"})

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
        
        # Step 1: Try ML Model first - Let ML handle weather internally
        try:
            from .ml_utils import tree_predictor
            print(f"[DEBUG] Attempting ML prediction for {tree_species_name} in {county_name}")
            env = county.environment if hasattr(county, 'environment') else None
            print(f"[DEBUG] County environment found: {env is not None}")
            
            # Build ML features without manual weather injection
            if env:
                ml_features = {
                    'county': county_name,
                    'region': getattr(env, 'climate_zone', 'Central'),
                    'altitude_m': (env.altitude_m_min + env.altitude_m_max) / 2,
                    'soil_ph': 6.5,
                    'soil_type': env.soil_type,
                    'tree_species': tree_species_name,
                    'planting_season': planting_season,
                    'planting_method': planting_method,
                    'care_level': care_level,
                    'water_source': 'Rain-fed',
                    'tree_age_months': 12,
                    'latitude': county.latitude,
                    'longitude': county.longitude
                }
            else:
                ml_features = {
                    'county': county_name,
                    'region': 'Central',
                    'altitude_m': 1500,
                    'soil_ph': 6.5,
                    'soil_type': 'Loam',
                    'tree_species': tree_species_name,
                    'planting_season': planting_season,
                    'planting_method': planting_method,
                    'care_level': care_level,
                    'water_source': 'Rain-fed',
                    'tree_age_months': 12,
                    'latitude': county.latitude if hasattr(county, 'latitude') else None,
                    'longitude': county.longitude if hasattr(county, 'longitude') else None
                }
            
            print(f"[DEBUG] ML features: {ml_features}")
            ml_result = tree_predictor.predict_survival(ml_features)
            print(f"[DEBUG] ML result: {ml_result}")
            if ml_result['success']:
                ml_prediction = ml_result.get('survival_probability', ml_result.get('survival_percentage', 0))
                print(f"   ML Model prediction: {ml_prediction:.1f}%")
                ml_used = True
            else:
                ml_used = False
                print(f"   ML model failed: {ml_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"   ML model failed: {e}")
            ml_used = False
            ml_prediction = None
        
        # Step 2: Calculate Species-Specific Playbook prediction
        playbook_prediction = base_survival_rate
        
        # SPECIES-SPECIFIC ADJUSTMENTS (This was missing!)
        species_adjustments = {
            'Pine': {'highland_bonus': 15, 'lowland_penalty': -20, 'optimal_temp': (10, 22)},
            'Cypress': {'highland_bonus': 12, 'lowland_penalty': -18, 'optimal_temp': (12, 22)},
            'Grevillea': {'highland_bonus': 8, 'lowland_penalty': -10, 'optimal_temp': (15, 28)},
            'Neem': {'drought_bonus': 15, 'highland_penalty': -15, 'optimal_temp': (24, 34)},
            'Indigenous Mix': {'adaptation_bonus': 10, 'optimal_temp': (12, 26)},
            'Eucalyptus': {'versatile_bonus': 5, 'optimal_temp': (18, 32)}
        }
        
        species_config = species_adjustments.get(tree_species_name, {})
        
        # Apply species-specific environmental matching
        env = county.environment if hasattr(county, 'environment') else None
        if env:
            avg_altitude = (env.altitude_m_min + env.altitude_m_max) / 2
            avg_temp = (env.temperature_c_min + env.temperature_c_max) / 2
            
            # Highland/Lowland species matching
            if 'highland_bonus' in species_config and avg_altitude > 1500:
                playbook_prediction += species_config['highland_bonus']
            elif 'lowland_penalty' in species_config and avg_altitude > 1500:
                playbook_prediction += species_config['lowland_penalty']
            
            if 'highland_penalty' in species_config and avg_altitude > 1500:
                playbook_prediction += species_config['highland_penalty']
            elif 'drought_bonus' in species_config and avg_altitude < 1000:
                playbook_prediction += species_config['drought_bonus']
            
            # Temperature matching
            if 'optimal_temp' in species_config:
                temp_min, temp_max = species_config['optimal_temp']
                if temp_min <= avg_temp <= temp_max:
                    playbook_prediction += 8  # Optimal temperature bonus
                elif avg_temp < temp_min - 5 or avg_temp > temp_max + 5:
                    playbook_prediction -= 12  # Temperature stress penalty
            
            # Adaptation bonuses
            if 'adaptation_bonus' in species_config:
                playbook_prediction += species_config['adaptation_bonus']
            if 'versatile_bonus' in species_config:
                playbook_prediction += species_config['versatile_bonus']
        
        # Apply seasonal adjustments
        if seasonal_bonus != 0:
            playbook_prediction += seasonal_bonus
        
        # Care level adjustments
        care_adjustments = {'High': 8, 'Medium': 0, 'Low': -5}
        playbook_prediction += care_adjustments.get(care_level, 0)
        playbook_prediction = max(15, min(95, playbook_prediction))
        
        print(f"   Playbook prediction: {playbook_prediction:.1f}%")
        
        # Step 3: Combine predictions with ML failure handling
        if ml_prediction is not None and 'ml_used' in locals() and ml_used:
            # Use weighted average: 50% ML model + 50% playbook when ML works
            base_prediction = (ml_prediction * 0.5) + (playbook_prediction * 0.5)
            print(f"   Hybrid prediction (50% ML + 50% Playbook): {base_prediction:.1f}%")
        else:
            # Penalty for no ML - reduce playbook confidence
            base_prediction = playbook_prediction * 0.85
            print(f"   Using playbook only (85% confidence): {base_prediction:.1f}%")
        
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
        
        # Add species differentiation factor
        SPECIES_VARIANCE = {
            "Grevillea": 1.0,
            "Pine": 0.92,
            "Cypress": 0.88,
            "Neem": 0.95,
            "Indigenous Mix": 1.05,
            "Eucalyptus": 0.90
        }
        
        species_factor = SPECIES_VARIANCE.get(tree_species_name, 0.9)
        final_survival_rate = final_survival_rate * species_factor
        
        # Cap the final score properly
        final_survival_rate = max(5, min(95, final_survival_rate))
        print(f"   Species factor ({tree_species_name}): {species_factor}, Final capped: {final_survival_rate:.1f}%")
        
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

        # Save weather snapshot and prediction (if logged in)
        weather_snapshot = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Save weather snapshot for audit trail
            from .models import WeatherSnapshot
            if hasattr(county, 'latitude') and hasattr(county, 'longitude'):
                try:
                    from .weather_service import WeatherService
                    live_weather = WeatherService.get_weather(county.latitude, county.longitude)
                    if live_weather:
                        weather_snapshot = WeatherSnapshot.objects.create(
                            latitude=county.latitude,
                            longitude=county.longitude,
                            temperature_c=live_weather['temperature'],
                            humidity=live_weather['humidity'],
                            rain_mm_hour=live_weather['rainfall'],
                            wind_speed=live_weather['wind_speed'],
                            cached=False
                        )
                except Exception as e:
                    print(f"Failed to save weather snapshot: {e}", flush=True)
            
            # Calculate confidence based on data sources
            from .utils import get_confidence_label
            has_live_weather = weather_snapshot is not None
            used_ml = ml_prediction is not None and 'ml_used' in locals() and ml_used
            confidence_label = get_confidence_label(has_live_weather, used_ml)
            
            TreePrediction.objects.create(
                user=request.user,
                tree_species=tree_species_name,
                county=county_name,
                region=getattr(county, 'environment', None) and county.environment.climate_zone or 'Unknown',
                soil_type=species.soil,
                rainfall_mm=weather_snapshot.rain_mm_hour * 24 if weather_snapshot else 0,
                temperature_c=weather_snapshot.temperature_c if weather_snapshot else 0,
                altitude_m=getattr(county, 'environment', None) and (county.environment.altitude_m_min + county.environment.altitude_m_max) / 2 or 0,
                soil_ph=6.5,
                planting_season=planting_season,
                planting_method=planting_method,
                care_level=care_level,
                water_source="Rain-fed",
                tree_age_months=12,
                survival_probability=final_survival_rate,
                survival_level=risk_level.lower(),
                confidence_level=confidence_label.lower(),
                model_version="v2.0.0",
                risk_factors='["Seasonal timing", "Environmental conditions"]',
                explanation_reasons='["Expert knowledge", "Environmental compatibility", "Live weather data"]',
                weather_snapshot=weather_snapshot
            )

        # Enhanced response with Phase 2 improvements
        from .utils import get_confidence_label, get_risk_label
        has_live_weather = hasattr(county, 'latitude') and hasattr(county, 'longitude')
        used_ml = ml_prediction is not None and 'ml_used' in locals() and ml_used
        confidence_level = get_confidence_label(has_live_weather, used_ml)
        prediction_text = "Likely to Survive" if final_survival_rate >= 60 else "Challenging Conditions"
        clean_risk_label = get_risk_label(final_survival_rate)
        
        # Add ML model confidence
        ml_confidence = "High" if ml_prediction and ml_prediction > 40 else "Medium" if ml_prediction and ml_prediction > 25 else "Low" if ml_prediction else "No ML Data"
        
        # Generate species-specific risks and reasons
        risks = []
        reasons = []
        
        # Species-specific assessment
        if tree_species_name in ['Pine', 'Cypress']:
            if county_name in ['Mombasa', 'Kilifi', 'Garissa', 'Turkana']:
                risks.append("Highland species struggle in hot coastal/arid conditions")
            else:
                reasons.append("Highland species thrive in cool, moist conditions")
        elif tree_species_name == 'Neem':
            if county_name in ['Nyeri', 'Meru', 'Nakuru']:
                risks.append("Lowland species may not tolerate highland cold")
            else:
                reasons.append("Excellent drought and heat tolerance")
        elif tree_species_name == 'Grevillea':
            reasons.append("Good adaptation to highland agroforestry")
        elif tree_species_name == 'Indigenous Mix':
            reasons.append("Native species naturally adapted to local conditions")
        
        # Seasonal risks
        if 'Dry' in planting_season and tree_species_name not in ['Neem']:
            risks.append("Dry season planting increases water stress")
        
        # Care level impact
        if care_level == 'High':
            reasons.append("High care level improves survival chances")
        elif care_level == 'Low' and final_survival_rate < 70:
            risks.append("Low care may reduce survival in challenging conditions")
        
        # Environmental matching
        if final_survival_rate >= 80:
            reasons.append("Optimal environmental match for this species")
        
        return JsonResponse({
            "success": True,
            "survival_percentage": round(final_survival_rate, 1),
            "survival_probability": round(final_survival_rate, 1),
            "confidence_level": confidence_level,
            "prediction": prediction_text,
            "risk_level": clean_risk_label,
            "environmental_risk": clean_risk_label,
            "prediction_confidence": confidence_level,
            "risks": risks,
            "reasons": reasons,
            "model_version": "v2.0.0",
            "ml_confidence": ml_confidence,
            "after_care": after_care,
            "explanation": explanation,
            "species_rank": county_species.species_rank,
            "match_score": county_species.environmental_match_score,
            "recommendation_reason": county_species.recommendation_reason,
            "alternative_species": good_alternatives[:2] if 'good_alternatives' in locals() else [],
            "weather_used": has_live_weather,
            "ml_used": used_ml,
            "prediction_sources": {
                "ml_prediction": ml_prediction,
                "playbook_prediction": playbook_prediction,
                "experience_bonus": user_experience_bonus,
                "final_prediction": round(final_survival_rate, 1)
            }
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

@csrf_exempt
@require_http_methods(["POST"])
def detect_county_api(request):
    """
    Detect nearest county from GPS coordinates
    """
    try:
        data = json.loads(request.body)
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        
        from .utils import detect_nearest_county
        county = detect_nearest_county(lat, lon)
        
        return JsonResponse({
            "success": True,
            "county": county,
            "note": "Suggested county based on approximate location. Please confirm.",
            "coordinates": {"lat": lat, "lon": lon}
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
            "county": None
        })
