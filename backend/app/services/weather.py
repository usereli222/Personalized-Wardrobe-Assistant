"""Fetch weather data and derive lighting conditions."""

from datetime import datetime, timezone

import httpx

from app.core.config import settings


async def get_weather(lat: float, lon: float) -> dict:
    """Fetch current weather from OpenWeatherMap."""
    if not settings.OPENWEATHERMAP_API_KEY:
        # Return mock data for development
        return {
            "cloud_cover": 50,
            "weather_main": "Clouds",
            "description": "scattered clouds",
            "temp": 22.0,
            "sunrise": 1700000000,
            "sunset": 1700040000,
            "current_time": int(datetime.now(timezone.utc).timestamp()),
        }

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.OPENWEATHERMAP_API_KEY,
        "units": "metric",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    return {
        "cloud_cover": data["clouds"]["all"],
        "weather_main": data["weather"][0]["main"],
        "description": data["weather"][0]["description"],
        "temp": data["main"]["temp"],
        "sunrise": data["sys"]["sunrise"],
        "sunset": data["sys"]["sunset"],
        "current_time": int(datetime.now(timezone.utc).timestamp()),
    }


def get_lighting_condition(weather: dict) -> str:
    """
    Derive lighting condition from weather data.

    Returns one of: bright, overcast, golden_hour, indoor
    """
    current = weather["current_time"]
    sunrise = weather["sunrise"]
    sunset = weather["sunset"]

    # Night time → indoor lighting
    if current < sunrise or current > sunset:
        return "indoor"

    # Golden hour: within 1 hour of sunrise or sunset
    if current - sunrise < 3600 or sunset - current < 3600:
        return "golden_hour"

    # Overcast: high cloud cover
    if weather["cloud_cover"] > 70:
        return "overcast"

    return "bright"
