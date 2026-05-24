from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import re
from django.db import IntegrityError
from datetime import datetime

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
    Predicts establishment survival probability using ML-first scoring.
    - Species is optional (returns recommendations if omitted)
    - Planting time can be provided as `planting_month` (1-12) or legacy `planting_season`
    - Planting method can be `Auto` (default), otherwise one of Seedling/Seeds/Transplant
    """
    try:
        data = json.loads(request.body)

        county_name = _normalize_county_name(data.get('county'))
        if not county_name:
            return JsonResponse({"success": False, "error": "Missing county"})

        tree_species_name = (data.get('tree_species') or "").strip()
        care_level = (data.get('care_level') or "Medium").strip() or "Medium"

        planting_season_raw = (data.get('planting_season') or "").strip()
        planting_month_raw = data.get('planting_month')
        requested_method_raw = (data.get('planting_method') or "").strip()

        def _coerce_month(value):
            try:
                m = int(value)
                return m if 1 <= m <= 12 else None
            except Exception:
                return None

        def _month_to_season_bucket(month: int) -> str:
            # MVP Kenya-wide approximation.
            if month in (3, 4, 5, 10, 11, 12):
                return "Wet"
            if month in (2, 6, 9):
                return "Transition"
            return "Dry"

        def _infer_month_from_legacy_season(season_text: str):
            season_lower = (season_text or "").lower().replace('–', '-').replace('—', '-')
            month_hints = {
                'jan': 1, 'january': 1,
                'feb': 2, 'february': 2,
                'mar': 3, 'march': 3,
                'apr': 4, 'april': 4,
                'may': 5,
                'jun': 6, 'june': 6,
                'jul': 7, 'july': 7,
                'aug': 8, 'august': 8,
                'sep': 9, 'sept': 9, 'september': 9,
                'oct': 10, 'october': 10,
                'nov': 11, 'november': 11,
                'dec': 12, 'december': 12,
            }
            for key, m in month_hints.items():
                if key in season_lower:
                    return m
            return None

        month = _coerce_month(planting_month_raw)
        if month is None:
            month = _infer_month_from_legacy_season(planting_season_raw)
        if month is None:
            month = datetime.now().month

        planting_season = _month_to_season_bucket(month)
        if planting_season_raw:
            season_lower = planting_season_raw.lower()
            if 'wet' in season_lower or 'rain' in season_lower:
                planting_season = 'Wet'
            elif 'dry' in season_lower:
                planting_season = 'Dry'
            elif 'transition' in season_lower:
                planting_season = 'Transition'

        def _normalize_method(value: str) -> str:
            v = (value or '').strip()
            if not v or v.lower() == 'auto':
                return 'Auto'
            if v.lower() in ['seedling', 'seedlings']:
                return 'Seedling'
            if v.lower() in ['seeds', 'direct seeding', 'direct-seeding']:
                return 'Seeds'
            if v.lower() in ['transplant', 'transplanting']:
                return 'Transplant'
            return v

        requested_method = _normalize_method(requested_method_raw)

        # Get county (create if needed)
        county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            try:
                county = County.objects.create(name=county_name)
            except IntegrityError:
                county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            return JsonResponse({"success": False, "error": f"County '{county_name}' not found"})

        # Optional species resolution (for metadata / care fallbacks)
        species_obj = None
        county_species_obj = None
        if tree_species_name:
            species_obj = Species.objects.filter(name__iexact=tree_species_name).first()
            if not species_obj:
                _ensure_default_species()
                species_obj = Species.objects.filter(name__iexact=tree_species_name).first()
            if not species_obj:
                return JsonResponse({"success": False, "error": f"Species '{tree_species_name}' not found"})

            county_species_obj = CountySpecies.objects.filter(county=county, species=species_obj).first()
            if not county_species_obj:
                _ensure_default_county_species(county)
                county_species_obj = CountySpecies.objects.filter(county=county, species=species_obj).first()

        # Environment defaults
        env = county.environment if hasattr(county, 'environment') else None
        if env:
            region = getattr(env, 'climate_zone', 'Central')
            altitude_m = (env.altitude_m_min + env.altitude_m_max) / 2
            soil_type = getattr(env, 'soil_type', 'Loam')
            rainfall_mm = (env.rainfall_mm_min + env.rainfall_mm_max) / 2
            temperature_c = (env.temperature_c_min + env.temperature_c_max) / 2
        else:
            region = 'Central'
            altitude_m = 1500
            soil_type = 'Loam'
            rainfall_mm = 800
            temperature_c = 22

        # Internal ML categories
        # Note: the trained dataset includes: Seedling, Direct Seeding, Cutting.
        # The UI uses: Seedling, Seeds, Transplant. We map UI 'Transplant' -> model 'Cutting'.
        encoder_methods = []
        try:
            encoder = getattr(tree_predictor, 'encoders', {}) or {}
            method_encoder = encoder.get('planting_method')
            if method_encoder is not None and hasattr(method_encoder, 'classes_'):
                encoder_methods = [str(x) for x in list(method_encoder.classes_)]
        except Exception:
            encoder_methods = []

        internal_methods = encoder_methods or ['Seedling', 'Direct Seeding', 'Cutting']
        ui_to_internal = {
            'Seedling': 'Seedling',
            'Seeds': 'Direct Seeding',
            'Transplant': 'Cutting',
        }
        internal_to_ui = {
            'Seedling': 'Seedling',
            'Direct Seeding': 'Seeds',
            'Cutting': 'Transplant',
        }

        def _best_method_for_species(species_name: str):
            if requested_method != 'Auto':
                methods_to_try = [ui_to_internal.get(requested_method, requested_method)]
            else:
                methods_to_try = list(internal_methods)

            scored = []
            for internal_method in methods_to_try:
                features = {
                    'county': county_name,
                    'region': region,
                    'altitude_m': altitude_m,
                    'soil_ph': 6.5,
                    'soil_type': soil_type,
                    'rainfall_mm': rainfall_mm,
                    'temperature_c': temperature_c,
                    'tree_species': species_name,
                    'planting_season': planting_season,
                    'planting_method': internal_method,
                    'care_level': care_level,
                    'water_source': 'Rain-fed',
                    'tree_age_months': 12,
                    'latitude': getattr(county, 'latitude', None),
                    'longitude': getattr(county, 'longitude', None),
                    'use_live_weather': False,
                }

                result = tree_predictor.predict_survival(features)
                if not result.get('success'):
                    continue

                score = float(result.get('survival_probability') or 0.0)
                scored.append({
                    'score': score,
                    'method_internal': internal_method,
                    'method_ui': internal_to_ui.get(internal_method, internal_method),
                    'ml_used': result.get('demo_mode') is not True,
                    'weather_used': bool(result.get('weather_used', False)),
                    'raw': result,
                })

            if not scored:
                return None

            scored.sort(key=lambda x: x['score'], reverse=True)
            best = scored[0]

            # If the model cannot distinguish between methods (scores are identical/near-identical),
            # default to Seedling for clearer guidance and label it as a default choice.
            if requested_method == 'Auto' and len(scored) > 1:
                scores = [x['score'] for x in scored]
                spread = max(scores) - min(scores)
                if spread <= 0.1:
                    best = next((x for x in scored if x['method_ui'] == 'Seedling'), best)
                    best = dict(best)
                    best['method_ui'] = f"{best['method_ui']} (default — methods score similarly)"

            return best

        # Candidate species: prefer county-specific mappings; fallback to a small default list.
        county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')
        if not county_species_qs.exists():
            _ensure_default_species()
            _ensure_default_county_species(county)
            county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')

        candidate_species = [cs.species.name for cs in county_species_qs] if county_species_qs.exists() else list(
            Species.objects.values_list('name', flat=True)[:20]
        )

        recommendations = []
        for sname in candidate_species:
            best = _best_method_for_species(sname)
            if not best:
                continue
            recommendations.append({
                'species': sname,
                'survival_percentage': round(best['score'], 1),
                'recommended_method': best['method_ui'],
            })

        recommendations.sort(key=lambda r: r['survival_percentage'], reverse=True)
        recommendations = recommendations[:5]

        focal_species = tree_species_name or (recommendations[0]['species'] if recommendations else '')
        if not focal_species:
            return JsonResponse({"success": False, "error": "No species available to recommend for this county yet"})

        focal_best = _best_method_for_species(focal_species)
        if not focal_best:
            return JsonResponse({"success": False, "error": "Prediction failed for the selected inputs"})

        final_survival_rate = float(focal_best['score'])
        used_ml = bool(focal_best['ml_used'])
        weather_used = bool(focal_best['weather_used'])

        print(f"[PREDICTION] {county_name} -> {focal_species}")
        print(f"   ML-only survival rate: {final_survival_rate}%")
        print(f"   Planting: month={month}, season_bucket={planting_season}")
        print(f"   Recommended method: {focal_best['method_ui']}")

        # Text-only explanation/care
        try:
            from .groq_ai import generate_tree_explanation
            explanation = generate_tree_explanation({
                'species': focal_species,
                'county': county_name,
                'season': planting_season_raw or planting_season,
                'survival_rate': final_survival_rate,
                'risk_level': 'Low' if final_survival_rate >= 75 else 'Medium' if final_survival_rate >= 60 else 'High',
                'reason': (county_species_obj.recommendation_reason if county_species_obj else 'Based on location and planting time'),
                'seasonal_bonus': 0,
                'best_season': (species_obj.best_season if species_obj else 'Wet season'),
            })
        except Exception:
            if final_survival_rate >= 75:
                explanation = f"{focal_species} is a strong match for {county_name} in this planting period."
            elif final_survival_rate >= 60:
                explanation = f"{focal_species} can do well in {county_name} in this planting period, with consistent care."
            else:
                explanation = f"{focal_species} may struggle in {county_name} in this planting period. Consider another species or better timing."

        try:
            from .groq_ai import generate_care_instructions
            after_care = generate_care_instructions({
                'species': focal_species,
                'county': county_name,
                'season': planting_season_raw or planting_season,
                'survival_rate': final_survival_rate,
                'risk_level': 'Low' if final_survival_rate >= 75 else 'Medium' if final_survival_rate >= 60 else 'High',
                'planting_method': focal_best['method_ui'],
                'base_care': (species_obj.care_instructions if species_obj else []),
            })
        except Exception:
            after_care = (species_obj.care_instructions if species_obj and species_obj.care_instructions else [
                "Mulch around the base to keep moisture.",
                "Protect the young tree from livestock.",
                "Weed around the tree regularly.",
                "Water consistently during dry weeks.",
            ])

        # Save weather snapshot and prediction (if logged in).
        # Only persist when the user explicitly requested a specific species.
        if hasattr(request, 'user') and request.user.is_authenticated and tree_species_name:
            weather_snapshot = None
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

            from .utils import get_confidence_label
            confidence_label = get_confidence_label(bool(weather_snapshot), used_ml)

            TreePrediction.objects.create(
                user=request.user,
                tree_species=focal_species,
                county=county_name,
                region=region,
                soil_type=soil_type,
                rainfall_mm=(weather_snapshot.rain_mm_hour * 24 if weather_snapshot else rainfall_mm),
                temperature_c=(weather_snapshot.temperature_c if weather_snapshot else temperature_c),
                altitude_m=altitude_m,
                soil_ph=6.5,
                planting_season=planting_season,
                planting_method=focal_best['method_ui'],
                care_level=care_level,
                water_source="Rain-fed",
                tree_age_months=12,
                survival_probability=final_survival_rate,
                survival_level=("low" if final_survival_rate >= 75 else "moderate" if final_survival_rate >= 60 else "high"),
                confidence_level=confidence_label.lower(),
                model_version="v2.0.0",
                risk_factors='["Seasonal timing", "Environmental conditions"]',
                explanation_reasons='["ML model", "Environmental context"]',
                weather_snapshot=weather_snapshot
            )

        from .utils import get_confidence_label, get_risk_label
        confidence_level = get_confidence_label(weather_used, used_ml)
        prediction_text = "Likely to Survive" if final_survival_rate >= 60 else "Challenging Conditions"
        clean_risk_label = get_risk_label(final_survival_rate)

        ml_confidence = "High" if used_ml else "Low"

        # Keep lightweight, non-numeric risks/reasons for UX.
        risks = []
        reasons = []
        if planting_season == 'Dry' and focal_species not in ['Neem']:
            risks.append("Dry season planting increases water stress")
        if care_level == 'High':
            reasons.append("High care level improves survival chances")
        if final_survival_rate >= 75:
            reasons.append("Good match for local conditions")

        alternative_species = [r['species'] for r in recommendations if r['species'] != focal_species][:2]

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
            "recommended_method": focal_best['method_ui'],
            "recommended_species": recommendations,
            "planting_season": planting_season,
            "planting_month": month,
            "species_rank": (county_species_obj.species_rank if county_species_obj else None),
            "match_score": (county_species_obj.environmental_match_score if county_species_obj else None),
            "recommendation_reason": (county_species_obj.recommendation_reason if county_species_obj else None),
            "alternative_species": alternative_species,
            "weather_used": weather_used,
            "ml_used": used_ml,
            "prediction_sources": {
                "ml_prediction": round(final_survival_rate, 1),
                "playbook_prediction": None,
                "experience_bonus": 0,
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
        data = {}
        try:
            if request.body:
                data = json.loads(request.body)
        except Exception:
            data = {}

        def _first(*keys):
            for k in keys:
                v = data.get(k)
                if v is None:
                    v = request.POST.get(k)
                if v not in (None, ""):
                    return v
            return None

        lat_raw = _first('lat', 'latitude')
        lon_raw = _first('lon', 'lng', 'longitude')
        lat = float(lat_raw)
        lon = float(lon_raw)
        
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
