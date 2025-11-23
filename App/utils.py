# App/utils.py
from .models import County, CountyEnvironment, Species

def get_county_environment(county_name):
    """
    Returns environmental data for a given county.
    """
    try:
        county = County.objects.get(name=county_name)
        env = county.environment  # thanks to related_name="environment"
        
        return {
            "rainfall_mm_min": env.rainfall_mm_min,
            "rainfall_mm_max": env.rainfall_mm_max,
            "temperature_c_min": env.temperature_c_min,
            "temperature_c_max": env.temperature_c_max,
            "soil_type": env.soil_type,
            "altitude_m_min": env.altitude_m_min,
            "altitude_m_max": env.altitude_m_max,
            "soil_ph_min": env.soil_ph_min,
            "soil_ph_max": env.soil_ph_max,
            "climate_zone": env.climate_zone,
            "best_season": env.best_season
        }
        
    except County.DoesNotExist:
        print(f"County '{county_name}' not found.")
        return None
    except CountyEnvironment.DoesNotExist:
        print(f"Environment for county '{county_name}' not found.")
        return None


def build_prediction_input(user_county_name, species_name, planting_method, planting_season):
    """
    Prepares the input dictionary for the prediction model.
    Combines user input (species, planting method, planting season)
    with auto-filled county environment and species info.
    """
    # 1. Get county environment
    env = get_county_environment(user_county_name)
    if not env:
        raise ValueError(f"County '{user_county_name}' environment not found")

    # 2. Get species info
    try:
        species_obj = Species.objects.get(name=species_name)
    except Species.DoesNotExist:
        raise ValueError(f"Species '{species_name}' not found")

    # 3. Combine everything into a single dictionary
    model_input = {
        "species": species_obj.name,
        "soil": species_obj.soil,
        "rainfall": species_obj.rainfall,
        "temperature": species_obj.temperature,
        "care_level": species_obj.care_level,
        "best_season": species_obj.best_season,
        "planting_method": planting_method,
        "planting_season": planting_season,
        "water": species_obj.water,
        "planting_guide": species_obj.planting_guide,
        "care_instructions": species_obj.care_instructions,
        **env  # this includes county rainfall, temperature, soil_type, altitude, pH, etc.
    }

    return model_input
