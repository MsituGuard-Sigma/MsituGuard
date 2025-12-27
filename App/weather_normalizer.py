def normalize_rainfall(weather_data):
    """
    Converts OpenWeather rainfall into daily rainfall estimate
    """
    hourly_rain = weather_data.get("rainfall", 0.0)
    daily_rain = hourly_rain * 24

    if daily_rain < 2:
        rain_status = "Dry"
    elif 2 <= daily_rain <= 10:
        rain_status = "Optimal"
    else:
        rain_status = "Excess"

    return {
        "daily_rain_mm": round(daily_rain, 2),
        "rain_status": rain_status
    }

def get_confidence_label(has_live_weather, used_ml):
    """Get confidence level based on data sources used"""
    if has_live_weather and used_ml:
        return "High"
    elif used_ml:
        return "Medium"
    return "Low"