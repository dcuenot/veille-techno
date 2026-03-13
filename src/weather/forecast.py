from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass(frozen=True)
class WeatherData:
    city: str
    description: str
    temp_current: float
    temp_min: float
    temp_max: float


def fetch_weather(lat: float, lon: float, api_key: str, timeout: int = 15) -> WeatherData | None:
    try:
        response = requests.get(
            OWM_URL,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "fr"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        logger.warning("Failed to fetch weather data")
        return None

    return WeatherData(
        city=data.get("name", ""),
        description=data["weather"][0]["description"],
        temp_current=data["main"]["temp"],
        temp_min=data["main"]["temp_min"],
        temp_max=data["main"]["temp_max"],
    )
