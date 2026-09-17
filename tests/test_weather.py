import httpx
import pytest

from services.weather import OpenMeteoWeatherService
from app.models import Location


@pytest.mark.asyncio
async def test_geocode_prefers_exact_name_over_similar_first_result():
    def handler(request):
        assert request.url.params["count"] == "10"
        return httpx.Response(200, json={"results": [
            {"name": "Lutsk", "latitude": 50.7, "longitude": 25.3, "country": "Ukraine"},
            {"name": "Lucknow", "latitude": 26.8, "longitude": 80.9, "country": "India"},
        ]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        location = await OpenMeteoWeatherService(client).geocode("Lucknow")
    assert location.name == "Lucknow"
    assert location.country == "India"


@pytest.mark.asyncio
async def test_fetch_requests_and_preserves_rain_and_gust_fields():
    def handler(request):
        assert request.url.params["latitude"] == "23.25469"
        assert "wind_gusts_10m" in request.url.params["current"]
        assert "precipitation_probability" in request.url.params["current"]
        assert "uv_index" in request.url.params["current"]
        assert request.url.params["daily"] == "precipitation_sum,wind_gusts_10m_max"
        return httpx.Response(200, json={
            "current": {
                "time": "2026-09-17T12:00",
                "temperature_2m": 27.8,
                "wind_speed_10m": 7.9,
                "wind_gusts_10m": 18.0,
                "precipitation": 0,
                "precipitation_probability": 2,
                "uv_index": 0,
                "weather_code": 1,
            },
            "hourly": {
                "time": ["2026-09-17T12:00"],
                "temperature_2m": [27.8],
                "wind_speed_10m": [7.9],
                "wind_gusts_10m": [18.0],
                "precipitation": [0],
                "precipitation_probability": [2],
                "uv_index": [0],
                "weather_code": [1],
            },
            "daily": {"precipitation_sum": [12.5], "wind_gusts_10m_max": [34.0]},
        })

    location = Location(name="Bhopal", latitude=23.25469, longitude=77.40289)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        snapshot = await OpenMeteoWeatherService(client).fetch(location)
    assert snapshot.precipitation_sum_mm == 12.5
    assert snapshot.wind_gust_kmh == 18.0
    assert snapshot.wind_gust_max_kmh == 34.0
    assert snapshot.precipitation_probability == 2
    assert snapshot.uv_index == 0
