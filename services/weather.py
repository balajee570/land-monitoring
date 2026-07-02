"""Current weather + short forecast via Open-Meteo (free, no API key).

Useful for agricultural land monitoring: current conditions plus a 7-day
temperature and rainfall outlook for the parcel's coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Weather:
    temperature_c: Optional[float] = None
    windspeed_kmh: Optional[float] = None
    weather_code: Optional[int] = None
    daily: Dict[str, List] = field(default_factory=dict)  # date/tmax/tmin/rain lists


_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
    96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


def describe(code: Optional[int]) -> str:
    return _WMO.get(code, "—") if code is not None else "—"


def get_weather(lat: float, lon: float) -> Optional[Weather]:
    try:
        import requests

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            "&timezone=auto&forecast_days=7"
        )
        data = requests.get(url, timeout=15).json()
        cur = data.get("current_weather", {})
        daily = data.get("daily", {})
        return Weather(
            temperature_c=cur.get("temperature"),
            windspeed_kmh=cur.get("windspeed"),
            weather_code=cur.get("weathercode"),
            daily={
                "date": daily.get("time", []),
                "tmax": daily.get("temperature_2m_max", []),
                "tmin": daily.get("temperature_2m_min", []),
                "rain": daily.get("precipitation_sum", []),
            },
        )
    except Exception:
        return None
