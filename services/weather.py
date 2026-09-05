from __future__ import annotations

from typing import Any

import httpx

from app.config import OPEN_METEO_FORECAST_URL, OPEN_METEO_GEOCODING_URL
from app.models import Location, WeatherSnapshot


class WeatherServiceError(RuntimeError):
    """A location could not be resolved or live weather could not be fetched."""


class OpenMeteoWeatherService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.client:
            response = await self.client.get(url, params=params)
        else:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def geocode(self, city: str) -> Location:
        try:
            # Open-Meteo can rank a similarly spelled city above the requested
            # city (for example, Lucknow vs. Lutsk). Prefer an exact name match
            # before retaining its documented first-result fallback.
            data = await self._get(OPEN_METEO_GEOCODING_URL, {"name": city, "count": 10, "language": "en", "format": "json"})
            results = data.get("results") or []
            requested_name = city.strip().casefold()
            result = next((item for item in results if item.get("name", "").casefold() == requested_name), results[0] if results else None)
            if not result:
                raise WeatherServiceError(f"No location found for {city!r}")
            return Location(name=result["name"], latitude=result["latitude"], longitude=result["longitude"], country=result.get("country"), timezone=result.get("timezone"))
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise WeatherServiceError("Could not resolve the location") from exc

    async def fetch(self, location: Location, target_period: str = "now") -> WeatherSnapshot:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,wind_speed_10m,precipitation,weather_code",
            "hourly": "temperature_2m,wind_speed_10m,precipitation,precipitation_probability,uv_index,weather_code",
            "forecast_days": 1,
            "timezone": "auto",
        }
        try:
            data = await self._get(OPEN_METEO_FORECAST_URL, params)
            current = data["current"]
            hourly = data["hourly"]
            index = self._hour_index(hourly["time"], target_period)
            return WeatherSnapshot(
                location=location, observed_at=hourly["time"][index] if target_period == "evening" else current["time"],
                target_period=target_period,
                temperature_c=hourly["temperature_2m"][index] if target_period == "evening" else current.get("temperature_2m"),
                wind_kmh=hourly["wind_speed_10m"][index] if target_period == "evening" else current.get("wind_speed_10m"),
                precipitation_mm=hourly["precipitation"][index] if target_period == "evening" else current.get("precipitation"),
                precipitation_probability=hourly["precipitation_probability"][index],
                uv_index=hourly["uv_index"][index],
                weather_code=hourly["weather_code"][index] if target_period == "evening" else current.get("weather_code"),
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise WeatherServiceError("Live weather is unavailable") from exc

    @staticmethod
    def _hour_index(times: list[str], target_period: str) -> int:
        if target_period == "evening":
            for index, value in enumerate(times):
                if "T18:" in value:
                    return index
        return 0
