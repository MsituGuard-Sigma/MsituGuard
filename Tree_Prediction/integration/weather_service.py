import requests
import time
from django.conf import settings

#in-memory cache 
_WEATHER_CACHE = {}
CACHE_TTL = 60 * 60  


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    @classmethod
    def get_weather(cls, lat, lon):
        """
        Get current weather data for coordinates with caching
        """
        cache_key = f"{lat},{lon}"
        now = time.time()

        #Check cache
        if cache_key in _WEATHER_CACHE:
            cached = _WEATHER_CACHE[cache_key]
            if now - cached["timestamp"] < CACHE_TTL:
                print(f"[WEATHER] Using cached data for {lat},{lon}")
                return cached["data"]

        #Call API
        if not settings.OPENWEATHER_API_KEY:
            print("[WEATHER] No API key configured, using fallback")
            return None

        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "appid": settings.OPENWEATHER_API_KEY,
        }

        try:
            print(f"[WEATHER] Calling API for {lat},{lon}", flush=True)
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            raw = response.json()

            #Extract data from 2.5 API 
            main = raw.get("main", {})
            wind = raw.get("wind", {})
            rain = raw.get("rain", {})
            weather = raw.get("weather", [{}])[0]
            
            weather_data = {
                "temperature": main.get("temp", 20.0),
                "humidity": main.get("humidity", 65),
                "wind_speed": wind.get("speed", 2.0),
                "rainfall": rain.get("1h", 0.0),
                "pressure": main.get("pressure", 1013),
                "weather_main": weather.get("main", "Clear"),
            }

            #Save to cache
            _WEATHER_CACHE[cache_key] = {
                "timestamp": now,
                "data": weather_data,
            }

            print(f"[WEATHER] API success: {weather_data['temperature']}°C, {weather_data['humidity']}% humidity", flush=True)
            return weather_data

        except Exception as e:
            print(f"[WEATHER] API failed: {e}")
            #Fail gracefully
            return None

    @classmethod
    def get_weather_summary(cls, lat, lon):
        """
        Get weather summary for display
        """
        weather = cls.get_weather(lat, lon)
        if not weather:
            return "Weather data unavailable"
        
        return f"{weather['temperature']:.1f}°C, {weather['humidity']}% humidity, {weather['weather_main']}"