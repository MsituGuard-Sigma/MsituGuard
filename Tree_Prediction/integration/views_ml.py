from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import re
import requests
from django.db import IntegrityError
from datetime import datetime

from App.models import County, CountySpecies, Species, TreePrediction
from .ml_utils import tree_predictor


def _normalize_county_name(value):
    if not value:
        return ""
    cleaned = value.strip()
    cleaned = re.sub(r"\s+county\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _get_altitude_from_gps(lat, lon):
    #Fetch real altitude for an exact GPS point using Open-Elevation (free, no key needed).
    #Returns None if the request fails so the caller can fall back to county default.
    try:
        resp = requests.get(
            f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}",
            timeout=3
        )
        data = resp.json()
        return float(data['results'][0]['elevation'])
    except Exception as e:
        print(f"[GPS] Open-Elevation lookup failed: {e}")
        return None


def _ensure_default_species():
    defaults_by_name = {
        "Indigenous Mix": {
            "soil": "Various", "rainfall": "600-1200mm", "temperature": "15-30°C",
            "care_level": "Low", "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling", "water": "Low to moderate",
            "planting_guide": ["Dig hole", "Add compost", "Plant seedling", "Mulch"],
            "care_instructions": ["Weed regularly", "Mulch base", "Protect from livestock"],
        },
        "Grevillea": {
            "soil": "Well-drained", "rainfall": "600-1000mm", "temperature": "15-28°C",
            "care_level": "Low", "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling", "water": "Low to moderate",
            "planting_guide": ["Plant in open area", "Space trees", "Water initially"],
            "care_instructions": ["Minimal maintenance", "Prune lightly", "Monitor pests"],
        },
        "Neem": {
            "soil": "Sandy to clay", "rainfall": "400-1200mm", "temperature": "20-35°C",
            "care_level": "Low", "best_season": "March–May, Oct–Dec",
            "planting_method": "Direct Seeding", "water": "Low",
            "planting_guide": ["Plant in warm area", "Water weekly first month", "Mulch"],
            "care_instructions": ["Drought tolerant", "Prune for shape", "Minimal inputs"],
        },
        "Eucalyptus": {
            "soil": "Well-drained", "rainfall": "600-1200mm", "temperature": "15-25°C",
            "care_level": "Medium", "best_season": "March–May, Oct–Dec",
            "planting_method": "Seedling", "water": "Moderate",
            "planting_guide": ["Plant seedlings", "Space 3-4m", "Water first 6 months"],
            "care_instructions": ["Monitor pests", "Prune lower branches"],
        },
        "Bamboo": {
            "soil": "Well-drained loam", "rainfall": "1000-2000mm", "temperature": "15-30°C",
            "care_level": "Medium", "best_season": "March–May, Oct–Dec",
            "planting_method": "Cutting", "water": "High",
            "planting_guide": ["Prepare deep hole", "Plant cutting at angle", "Water heavily", "Mulch"],
            "care_instructions": ["Water frequently", "Fertilise annually", "Remove dead culms"],
        },
    }
    species_objects = []
    for name, defaults in defaults_by_name.items():
        obj, _ = Species.objects.get_or_create(name=name, defaults=defaults)
        species_objects.append(obj)
    return species_objects


def _ensure_default_county_species(county):
    existing = CountySpecies.objects.filter(county=county)
    if existing.exists():
        return
    species_objects = list(Species.objects.all()[:8])
    if not species_objects:
        species_objects = _ensure_default_species()
    for idx, sp in enumerate(species_objects, start=1):
        CountySpecies.objects.get_or_create(
            county=county, species=sp,
            defaults={
                "survival_rate": 70.0, "species_rank": idx,
                "environmental_match_score": 70.0, "seasonal_performance": {},
                "recommendation_reason": "Baseline recommendation (no county-specific data loaded yet).",
            },
        )


@csrf_exempt
@require_http_methods(["POST"])
def get_species_recommendations(request):
    try:
        data = json.loads(request.body)
        county_name = _normalize_county_name(data.get('county'))
        if not county_name:
            return JsonResponse({"success": False, "error": "Missing county", "species": [], "playbook": {}})

        county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            try:
                county = County.objects.create(name=county_name)
            except IntegrityError:
                county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            return JsonResponse({"success": False, "error": "County not found", "species": [], "playbook": {}})

        _ensure_default_county_species(county)
        county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')
        species_list = [cs.species for cs in county_species_qs]

        playbook = {}
        for s in species_list:
            playbook[s.name] = {
                "planting_guide":    s.planting_guide,
                "best_month":        s.best_season,
                "planting_method":   getattr(s, "planting_method", "Seedling"),
                "soil":              s.soil,
                "rainfall_mm":       s.rainfall,
                "temperature_c":     s.temperature,
                "care_instructions": s.care_instructions,
            }

        return JsonResponse({"success": True, "species": [s.name for s in species_list], "playbook": playbook})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "species": [], "playbook": {}})


@csrf_exempt
@require_http_methods(["POST"])
def predict_tree_survival(request):
    """
    Predict tree survival probability.

    Accepts optional latitude/longitude from the user's device GPS.
    When GPS coordinates are provided:
      - Real altitude is fetched from Open-Elevation for that exact spot
      - Live weather (temperature, rainfall) is fetched at those coordinates
      - The model receives location-specific environment data instead of
        county-wide averages, producing a personalised prediction
    When GPS is not provided, falls back to county-level environment defaults.
    """
    try:
        data = json.loads(request.body)

        county_name = _normalize_county_name(data.get('county'))
        if not county_name:
            return JsonResponse({"success": False, "error": "Missing county"})

        tree_species_name    = (data.get('tree_species') or "").strip()
        care_level           = (data.get('care_level') or "Medium").strip() or "Medium"
        planting_season_raw  = (data.get('planting_season') or "").strip()
        planting_month_raw   = data.get('planting_month')
        requested_method_raw = (data.get('planting_method') or "").strip()

        #Read GPS coordinates sent by the frontend
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        has_gps  = user_lat is not None and user_lon is not None
        if has_gps:
            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except (TypeError, ValueError):
                has_gps = False

        def _coerce_month(value):
            try:
                m = int(value)
                return m if 1 <= m <= 12 else None
            except Exception:
                return None

        def _month_to_season_bucket(month):
            if month in (3, 4, 5, 10, 11, 12):
                return "Wet"
            if month in (2, 6, 9):
                return "Transition"
            return "Dry"

        def _infer_month_from_legacy_season(season_text):
            season_lower = (season_text or "").lower().replace('–', '-').replace('—', '-')
            month_hints = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
                'mar': 3, 'march': 3,   'apr': 4, 'april': 4,
                'may': 5, 'jun': 6,     'june': 6,
                'jul': 7, 'july': 7,    'aug': 8, 'august': 8,
                'sep': 9, 'sept': 9,    'september': 9,
                'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
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
            sl = planting_season_raw.lower()
            if 'wet' in sl or 'rain' in sl:
                planting_season = 'Wet'
            elif 'dry' in sl:
                planting_season = 'Dry'
            elif 'transition' in sl:
                planting_season = 'Transition'

        def _normalize_method(value):
            v = (value or '').strip()
            if not v or v.lower() == 'auto':
                return 'Auto'
            if v.lower() in ['seedling', 'seedlings']:
                return 'Seedling'
            if v.lower() in ['seeds', 'direct seeding', 'direct-seeding']:
                return 'Direct Seeding'
            if v.lower() in ['cutting', 'cuttings']:
                return 'Cutting'
            return v

        requested_method = _normalize_method(requested_method_raw)

        county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            try:
                county = County.objects.create(name=county_name)
            except IntegrityError:
                county = County.objects.filter(name__iexact=county_name).first()
        if not county:
            return JsonResponse({"success": False, "error": f"County '{county_name}' not found"})

        species_obj       = None
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

        #Start with county-level environment defaults
        env = county.environment if hasattr(county, 'environment') else None
        if env:
            region        = getattr(env, 'climate_zone', 'Central')
            altitude_m    = (env.altitude_m_min + env.altitude_m_max) / 2
            soil_type     = getattr(env, 'soil_type', 'Loam')
            rainfall_mm   = (env.rainfall_mm_min + env.rainfall_mm_max) / 2
            temperature_c = (env.temperature_c_min + env.temperature_c_max) / 2
        else:
            region        = 'Central'
            altitude_m    = 1500
            soil_type     = 'Loam'
            rainfall_mm   = 800
            temperature_c = 22

        #If the user shared GPS, upgrade to location-specific environment data.
        #This is what makes Westlands vs Karen vs Kibera give different scores.
        gps_altitude  = None
        location_note = "county-level data"
        if has_gps:
            gps_altitude = _get_altitude_from_gps(user_lat, user_lon)
            if gps_altitude is not None:
                altitude_m    = gps_altitude
                location_note = f"GPS altitude {gps_altitude:.0f}m"
                print(f"[GPS] Using real altitude {gps_altitude:.0f}m for ({user_lat},{user_lon})")
            else:
                print(f"[GPS] Altitude lookup failed — using county default {altitude_m}m")

        #Determine whether to fetch live weather.
        #We always enable it when GPS is available because the coordinates
        #give us weather at the exact planting spot, not just the county centre.
        use_live_weather = has_gps or bool(data.get('use_live_weather', False))

        encoder_methods = []
        try:
            method_encoder = (getattr(tree_predictor, 'encoders', {}) or {}).get('planting_method')
            if method_encoder is not None and hasattr(method_encoder, 'classes_'):
                encoder_methods = [str(x) for x in method_encoder.classes_]
        except Exception:
            pass
        internal_methods = encoder_methods or ['Seedling', 'Direct Seeding', 'Cutting']

        #Cache so each species is scored only once per request
        _prediction_cache = {}

        def _best_method_for_species(species_name):
            if species_name in _prediction_cache:
                return _prediction_cache[species_name]

            methods_to_try = [requested_method] if requested_method != 'Auto' else list(internal_methods)

            scored = []
            for method in methods_to_try:
                features = {
                    'county':           county_name,
                    'region':           region,
                    'altitude_m':       altitude_m,
                    'soil_ph':          6.5,
                    'soil_type':        soil_type,
                    'rainfall_mm':      rainfall_mm,
                    'temperature_c':    temperature_c,
                    'tree_species':     species_name,
                    'planting_season':  planting_season,
                    'planting_method':  method,
                    'care_level':       care_level,
                    'water_source':     'Rain-fed',
                    'tree_age_months':  12,
                    #Pass GPS so ml_utils can call WeatherService at the exact point
                    'latitude':         user_lat if has_gps else getattr(county, 'latitude', None),
                    'longitude':        user_lon if has_gps else getattr(county, 'longitude', None),
                    'use_live_weather': use_live_weather,
                }

                result = tree_predictor.predict_survival(features)
                if not result.get('success'):
                    continue

                scored.append({
                    'score':           float(result.get('survival_probability') or 0.0),
                    'method_internal': method,
                    'method_ui':       method,
                    'ml_used':         result.get('demo_mode') is not True,
                    'weather_used':    bool(result.get('weather_used', False)),
                    'raw':             result,
                })

            if not scored:
                return None

            scored.sort(key=lambda x: x['score'], reverse=True)
            best = scored[0]

            #Use species agronomic preference when ML scores are too close to distinguish
            if requested_method == 'Auto' and len(scored) > 1:
                spread = max(x['score'] for x in scored) - min(x['score'] for x in scored)
                if spread <= 2.0:
                    preferred = (getattr(tree_predictor, 'species_method_pref', {}) or {}).get(species_name)
                    if preferred:
                        match = next((x for x in scored if x['method_internal'] == preferred), None)
                        if match:
                            best = dict(match)

            _prediction_cache[species_name] = best
            return best

        county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')
        if not county_species_qs.exists():
            _ensure_default_species()
            _ensure_default_county_species(county)
            county_species_qs = CountySpecies.objects.filter(county=county).select_related('species')

        candidate_species = (
            [cs.species.name for cs in county_species_qs]
            if county_species_qs.exists()
            else list(Species.objects.values_list('name', flat=True)[:20])
        )

        recommendations = []
        for sname in candidate_species:
            best = _best_method_for_species(sname)
            if not best:
                continue
            recommendations.append({
                'species':             sname,
                'survival_percentage': round(best['score'], 1),
                'recommended_method':  best['method_ui'],
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
        used_ml             = bool(focal_best['ml_used'])
        weather_used        = bool(focal_best['weather_used'])

        print(f"[PREDICTION] {county_name} -> {focal_species}")
        print(f"  Survival: {final_survival_rate}%  |  Method: {focal_best['method_ui']}")
        print(f"  Season: {planting_season}  |  Location data: {location_note}")
        print(f"  GPS used: {has_gps}  |  Live weather: {use_live_weather}  |  ML: {used_ml}")

        try:
            from App.groq_ai import generate_tree_explanation
            explanation = generate_tree_explanation({
                'species':       focal_species,
                'county':        county_name,
                'season':        planting_season_raw or planting_season,
                'survival_rate': final_survival_rate,
                'risk_level':    'Low' if final_survival_rate >= 75 else 'Medium' if final_survival_rate >= 60 else 'High',
                'reason':        (county_species_obj.recommendation_reason if county_species_obj else 'Based on location and planting time'),
                'seasonal_bonus': 0,
                'best_season':   (species_obj.best_season if species_obj else 'Wet season'),
            })
        except Exception:
            if final_survival_rate >= 75:
                explanation = f"{focal_species} is a strong match for {county_name} in this planting period."
            elif final_survival_rate >= 60:
                explanation = f"{focal_species} can do well in {county_name} with consistent care."
            else:
                explanation = f"{focal_species} may struggle in {county_name}. Consider another species or better timing."

        try:
            from App.groq_ai import generate_care_instructions
            after_care = generate_care_instructions({
                'species':        focal_species,
                'county':         county_name,
                'season':         planting_season_raw or planting_season,
                'survival_rate':  final_survival_rate,
                'risk_level':     'Low' if final_survival_rate >= 75 else 'Medium' if final_survival_rate >= 60 else 'High',
                'planting_method': focal_best['method_ui'],
                'base_care':      (species_obj.care_instructions if species_obj else []),
            })
        except Exception:
            after_care = (
                species_obj.care_instructions
                if species_obj and species_obj.care_instructions
                else [
                    "Mulch around the base to keep moisture.",
                    "Protect the young tree from livestock.",
                    "Weed around the tree regularly.",
                    "Water consistently during dry weeks.",
                ]
            )

        if hasattr(request, 'user') and request.user.is_authenticated and tree_species_name:
            weather_snapshot = None
            from .models import WeatherSnapshot
            snap_lat = user_lat if has_gps else getattr(county, 'latitude', None)
            snap_lon = user_lon if has_gps else getattr(county, 'longitude', None)
            if snap_lat and snap_lon:
                try:
                    from .weather_service import WeatherService
                    live_weather = WeatherService.get_weather(snap_lat, snap_lon)
                    if live_weather:
                        weather_snapshot = WeatherSnapshot.objects.create(
                            latitude=snap_lat,
                            longitude=snap_lon,
                            temperature_c=live_weather['temperature'],
                            humidity=live_weather['humidity'],
                            rain_mm_hour=live_weather['rainfall'],
                            wind_speed=live_weather['wind_speed'],
                            cached=False
                        )
                except Exception as e:
                    print(f"Failed to save weather snapshot: {e}", flush=True)

            from .utils import get_confidence_label
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
                confidence_level=get_confidence_label(bool(weather_snapshot), used_ml).lower(),
                model_version="v2.0.0",
                risk_factors='["Seasonal timing", "Environmental conditions"]',
                explanation_reasons='["ML model", "Environmental context"]',
                weather_snapshot=weather_snapshot
            )

        from .utils import get_confidence_label, get_risk_label
        confidence_level = get_confidence_label(weather_used, used_ml)
        clean_risk_label = get_risk_label(final_survival_rate)

        risks   = []
        reasons = []
        if planting_season == 'Dry' and focal_species not in ['Neem', 'Acacia']:
            risks.append("Dry season planting increases water stress")
        if has_gps and gps_altitude is not None:
            if gps_altitude > 2000:
                risks.append(f"Your location is at high altitude ({gps_altitude:.0f}m) — choose species tolerant of cool temperatures")
            elif gps_altitude < 500:
                risks.append(f"Your location is at low altitude ({gps_altitude:.0f}m) — avoid highland species")
        if care_level == 'High':
            reasons.append("High care level improves survival chances")
        if final_survival_rate >= 75:
            reasons.append("Good match for local conditions")
        if has_gps:
            reasons.append("Prediction uses your exact GPS location for more accurate results")

        alternative_species = [r['species'] for r in recommendations if r['species'] != focal_species][:2]

        return JsonResponse({
            "success":               True,
            "survival_percentage":   round(final_survival_rate, 1),
            "survival_probability":  round(final_survival_rate, 1),
            "confidence_level":      confidence_level,
            "prediction":            "Likely to Survive" if final_survival_rate >= 60 else "Challenging Conditions",
            "risk_level":            clean_risk_label,
            "environmental_risk":    clean_risk_label,
            "prediction_confidence": confidence_level,
            "risks":                 risks,
            "reasons":               reasons,
            "model_version":         "v2.0.0",
            "ml_confidence":         "High" if used_ml else "Low",
            "after_care":            after_care,
            "explanation":           explanation,
            "recommended_method":    focal_best['method_ui'],
            "recommended_species":   recommendations,
            "planting_season":       planting_season,
            "planting_month":        month,
            "species_rank":          (county_species_obj.species_rank if county_species_obj else None),
            "match_score":           (county_species_obj.environmental_match_score if county_species_obj else None),
            "recommendation_reason": (county_species_obj.recommendation_reason if county_species_obj else None),
            "alternative_species":   alternative_species,
            "weather_used":          weather_used,
            "ml_used":               used_ml,
            "gps_used":              has_gps,
            "gps_altitude_m":        gps_altitude,
            "location_note":         location_note,
            "prediction_sources": {
                "ml_prediction":    round(final_survival_rate, 1),
                "playbook_prediction": None,
                "experience_bonus": 0,
                "final_prediction": round(final_survival_rate, 1),
            }
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def get_county_environment(request):
    try:
        data = json.loads(request.body)
        county_name = data.get('county')
        county = County.objects.filter(name=county_name).first()
        if not county or not hasattr(county, "environment"):
            return JsonResponse({"success": False, "error": "County environment not found", "environment": {}})

        env = county.environment
        return JsonResponse({
            "success": True,
            "environment": {
                "altitude_m":    (env.altitude_m_min + env.altitude_m_max) / 2,
                "rainfall_mm":   (env.rainfall_mm_min + env.rainfall_mm_max) / 2,
                "temperature_c": (env.temperature_c_min + env.temperature_c_max) / 2,
                "soil_type":     env.soil_type,
                "best_season":   env.best_season,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "environment": {}})


@csrf_exempt
@require_http_methods(["POST"])
def detect_county_api(request):
    try:
        data = json.loads(request.body)
        lat  = float(data.get('lat'))
        lon  = float(data.get('lon'))

        from .utils import detect_nearest_county
        county = detect_nearest_county(lat, lon)

        return JsonResponse({
            "success":     True,
            "county":      county,
            "note":        "Suggested county based on approximate location. Please confirm.",
            "coordinates": {"lat": lat, "lon": lon}
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "county": None})