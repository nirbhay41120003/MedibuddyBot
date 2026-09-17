from __future__ import annotations

from datetime import datetime, timedelta
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
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise WeatherServiceError("Could not resolve the location") from exc

    async def fetch(self, location: Location, target_period: str = "now") -> WeatherSnapshot:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,precipitation_probability,uv_index,weather_code",
            "hourly": "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,precipitation_probability,uv_index,weather_code",
            "daily": "precipitation_sum,wind_gusts_10m_max",
            "forecast_days": 2,
            "timezone": "auto",
        }
        try:
            data = await self._get(OPEN_METEO_FORECAST_URL, params)
            current = data["current"]
            hourly = data["hourly"]
            daily = data["daily"]
            index = self._hour_index(hourly["time"], target_period, current["time"])
            daily_index = 1 if target_period == "tomorrow" else 0
            return WeatherSnapshot(
                location=location, observed_at=current["time"] if target_period == "now" else hourly["time"][index],
                target_period=target_period,
                temperature_c=current.get("temperature_2m") if target_period == "now" else hourly["temperature_2m"][index],
                wind_kmh=current.get("wind_speed_10m") if target_period == "now" else hourly["wind_speed_10m"][index],
                precipitation_mm=current.get("precipitation") if target_period == "now" else hourly["precipitation"][index],
                precipitation_probability=current.get("precipitation_probability") if target_period == "now" else hourly["precipitation_probability"][index],
                uv_index=current.get("uv_index") if target_period == "now" else hourly["uv_index"][index],
                weather_code=current.get("weather_code") if target_period == "now" else hourly["weather_code"][index],
                precipitation_sum_mm=daily["precipitation_sum"][daily_index],
                wind_gust_kmh=current.get("wind_gusts_10m") if target_period == "now" else hourly["wind_gusts_10m"][index],
                wind_gust_max_kmh=daily["wind_gusts_10m_max"][daily_index],
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise WeatherServiceError("Live weather is unavailable") from exc

    @staticmethod
    def _hour_index(times: list[str], target_period: str, current_time: str | None = None) -> int:
        if target_period == "evening":
            for index, value in enumerate(times):
                if "T18:" in value:
                    return index
        if target_period == "night":
            for index, value in enumerate(times):
                if "T21:" in value:
                    return index
        if target_period == "tomorrow" and current_time:
            current = datetime.fromisoformat(current_time)
            target_date = current.date() + timedelta(days=1)
            target_hour = current.strftime("%H:")
            target_prefix = f"{target_date.isoformat()}T{target_hour}"
            for index, value in enumerate(times):
                if value.startswith(target_prefix):
                    return index
        return 0
