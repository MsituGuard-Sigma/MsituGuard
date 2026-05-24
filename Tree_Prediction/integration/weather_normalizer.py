def normalize_rainfall(weather_data):
    """
    Converts OpenWeather rainfall into daily rainfall estimate
    """
    # Accept either:
    # - hourly rain in mm (OpenWeather: rain['1h']) under keys: 'rainfall' or 'rain_mm_hour'
    # - daily rain estimate already computed under key: 'rainfall_mm'
    hourly_rain = weather_data.get("rainfall")
    if hourly_rain is None:
        hourly_rain = weather_data.get("rain_mm_hour")

    if hourly_rain is not None:
        daily_rain = float(hourly_rain) * 24
    else:
        daily_rain = float(weather_data.get("rainfall_mm", 0.0))

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