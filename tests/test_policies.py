from app.models import Location, WeatherSnapshot
from app.policies import match_sops


def weather(**changes) -> WeatherSnapshot:
    values = dict(location=Location(name="Test City", latitude=1, longitude=2), observed_at="2026-09-05T12:00", temperature_c=25, wind_kmh=10, precipitation_mm=0, precipitation_probability=10, uv_index=2, weather_code=1)
    values.update(changes)
    return WeatherSnapshot(**values)


def test_stronger_policy_wins_when_multiple_match():
    matches = match_sops(weather(wind_kmh=46, precipitation_mm=9), "cycling", None)
    assert matches[0].id == "SOP-WIND-CYCLE-01"
    assert {item.id for item in matches} >= {"SOP-WIND-CYCLE-01", "SOP-RAIN-TRAVEL-01"}


def test_no_policy_for_unknown_activity():
    assert match_sops(weather(), "unknown", None) == []


def test_paraphrased_bike_intent():
    from app.intent import extract_intent
    assert extract_intent("Can I take my bicycle out in Pune?").activity == "cycling"


def test_high_rain_probability_cycling_policy_applies():
    matches = match_sops(weather(precipitation_probability=83), "cycling", None)
    assert matches[0].id == "SOP-RAIN-CYCLE-02"


def test_fair_cycling_conditions_have_suitability_guidance():
    matches = match_sops(
        weather(
            temperature_c=26.9,
            wind_kmh=7.9,
            precipitation_mm=0,
            precipitation_probability=2,
            uv_index=0,
            weather_code=1,
        ),
        "cycling",
        None,
    )
    assert matches[0].id == "SOP-CYCLE-GOOD-01"


def test_city_extraction_uses_the_final_location_marker():
    from app.intent import extract_city
    assert extract_city("Is it safe to travel by motorcycle in Lucknow today?") == "Lucknow"
