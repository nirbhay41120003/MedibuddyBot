import httpx
import pytest

from services.weather import OpenMeteoWeatherService


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
