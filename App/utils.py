import math

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates"""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    
    return 2 * R * math.asin(math.sqrt(a))

def detect_nearest_county(lat, lon):
    """Find nearest county based on GPS coordinates"""
    from .models import County
    counties = County.objects.all()
    nearest = min(
        counties,
        key=lambda c: haversine(lat, lon, c.latitude, c.longitude)
    )
    return nearest.name

def get_confidence_label(has_weather, used_ml):
    """Calculate confidence level based on data sources used"""
    if has_weather and used_ml:
        return "High"
    if has_weather:
        return "Moderate"
    return "Low"

def get_risk_label(survival_score):
    """Get human-friendly risk label"""
    if survival_score >= 75:
        return "Low Risk – Good Conditions"
    elif survival_score >= 60:
        return "Moderate Risk – Extra Care Needed"
    else:
        return "High Risk – Challenging Conditions"

def get_county_environment(county_name):
    """Get county environment data"""
    from .models import County
    try:
        county = County.objects.get(name=county_name)
        if hasattr(county, 'environment'):
            env = county.environment
            return {
                'altitude_m': (env.altitude_m_min + env.altitude_m_max) / 2,
                'rainfall_mm': (env.rainfall_mm_min + env.rainfall_mm_max) / 2,
                'temperature_c': (env.temperature_c_min + env.temperature_c_max) / 2,
                'soil_type': env.soil_type,
                'climate_zone': env.climate_zone
            }
    except:
        pass
    return None