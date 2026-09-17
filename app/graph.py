from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.intent import extract_city, extract_intent_with_optional_llm
from app.models import Intent, Location, SOP, WeatherSnapshot
from app.policies import match_sops
from services.weather import OpenMeteoWeatherService, WeatherServiceError


class AdvisoryState(TypedDict, total=False):
    # Raw message is consumed only by interpretation/location nodes, never composer.
    message: str
    remembered_location: Location | None
    remembered_intent: Intent | None
    intent: Intent
    city: str | None
    location: Location
    weather: WeatherSnapshot
    selected_sop: SOP | None
    outcome: Literal["matched", "no_policy", "weather_unavailable", "location_needed", "intent_needed"]
    reply: str


async def _understand(state: AdvisoryState) -> dict:
    intent = await extract_intent_with_optional_llm(state["message"])
    city = extract_city(state["message"])
    prior = state.get("remembered_intent")
    # Only an explicit follow-up can inherit the prior activity. Greetings,
    # gibberish, and unrelated messages must never receive stale advice.
    if intent.activity == "unknown" and prior and not city and _is_contextual_follow_up(state["message"]):
        intent = intent.model_copy(update={
            "activity": prior.activity,
            "vulnerable_group": intent.vulnerable_group or prior.vulnerable_group,
        })
    return {"intent": intent, "city": city}


def _is_contextual_follow_up(message: str) -> bool:
    text = message.casefold().strip()
    return bool(re.fullmatch(
        r"(?:and\s+)?(?:what\s+about\s+)?(?:now|today|tonight|later|this evening|this afternoon)(?:\s+instead)?[?.!]*",
        text,
    ))


def _resolve_location(state: AdvisoryState) -> dict:
    # The async resolver runs in the next node; choose memory here to retain a real branch.
    if state["intent"].activity == "unknown":
        return {"outcome": "intent_needed"}
    if state.get("city"):
        return {}
    if state.get("remembered_location"):
        return {"location": state["remembered_location"]}
    return {"outcome": "location_needed"}


async def _geocode(state: AdvisoryState, service: OpenMeteoWeatherService) -> dict:
    if state.get("location"):
        return {}
    try:
        return {"location": await service.geocode(state["city"] or "")}
    except WeatherServiceError:
        return {"outcome": "weather_unavailable"}


async def _fetch_weather(state: AdvisoryState, service: OpenMeteoWeatherService) -> dict:
    try:
        return {"weather": await service.fetch(state["location"], state["intent"].target_period)}
    except WeatherServiceError:
        return {"outcome": "weather_unavailable"}


def _select_policy(state: AdvisoryState) -> dict:
    intent = state["intent"]
    matches = match_sops(state["weather"], intent.activity, intent.vulnerable_group)
    return {"selected_sop": matches[0] if matches else None, "outcome": "matched" if matches else "no_policy"}


def _format_facts(weather: WeatherSnapshot) -> str:
    # This is the sole path from weather values to language: all numbers came from Open-Meteo.
    facts = []
    if weather.temperature_c is not None: facts.append(f"temperature {weather.temperature_c:g}°C")
    if weather.wind_kmh is not None: facts.append(f"wind {weather.wind_kmh:g} km/h")
    if weather.precipitation_mm is not None: facts.append(f"precipitation {weather.precipitation_mm:g} mm")
    if weather.precipitation_probability is not None: facts.append(f"rain probability {weather.precipitation_probability:g}%")
    if weather.uv_index is not None: facts.append(f"UV index {weather.uv_index:g}")
    if weather.precipitation_sum_mm is not None: facts.append(f"today's precipitation forecast {weather.precipitation_sum_mm:g} mm")
    if weather.wind_gust_kmh is not None: facts.append(f"wind gusts {weather.wind_gust_kmh:g} km/h")
    if weather.wind_gust_max_kmh is not None: facts.append(f"maximum forecast gusts {weather.wind_gust_max_kmh:g} km/h")
    return ", ".join(facts)


def _compose(state: AdvisoryState) -> dict:
    """Policy-owned template composer. It intentionally does not read `message`."""
    outcome = state["outcome"]
    if outcome == "location_needed":
        return {"reply": "Please tell me the city so I can check live weather before applying a safety policy."}
    if outcome == "intent_needed":
        return {"reply": "Tell me the outdoor activity and city you want checked, for example: ‘Is it safe to cycle or go camping in Bhopal today?’"}
    if outcome == "weather_unavailable":
        return {"reply": "I couldn’t obtain live weather for that location, so I can’t apply a safety policy safely. Please try again shortly."}
    if outcome == "no_policy":
        return {"reply": "I have live weather, but no SOP covers that activity and situation, so I don’t have guidance to provide."}
    weather, sop = state["weather"], state["selected_sop"]
    assert sop is not None
    period = "this evening" if weather.target_period == "evening" else "now"
    return {"reply": (
        f"{sop.guidance} For {weather.location.name} {period}, Open-Meteo reports {_format_facts(weather)}. "
        f"Policy: {sop.id} — {sop.title} ({sop.severity.value} severity)."
    )}


def _after_location(state: AdvisoryState) -> str:
    return "compose" if state.get("outcome") in {"location_needed", "intent_needed"} else "geocode"


def _after_geocode(state: AdvisoryState) -> str:
    return "compose" if state.get("outcome") == "weather_unavailable" else "weather"


def _after_weather(state: AdvisoryState) -> str:
    return "compose" if state.get("outcome") == "weather_unavailable" else "policy"


def build_graph(service: OpenMeteoWeatherService | None = None):
    service = service or OpenMeteoWeatherService()

    async def geocode_node(state: AdvisoryState) -> dict:
        return await _geocode(state, service)

    async def weather_node(state: AdvisoryState) -> dict:
        return await _fetch_weather(state, service)

    graph = StateGraph(AdvisoryState)
    graph.add_node("understand", _understand)
    graph.add_node("resolve_location", _resolve_location)
    graph.add_node("geocode", geocode_node)
    graph.add_node("weather", weather_node)
    graph.add_node("policy", _select_policy)
    graph.add_node("compose", _compose)
    graph.add_edge(START, "understand")
    graph.add_edge("understand", "resolve_location")
    graph.add_conditional_edges("resolve_location", _after_location, {"compose": "compose", "geocode": "geocode"})
    graph.add_conditional_edges("geocode", _after_geocode, {"compose": "compose", "weather": "weather"})
    graph.add_conditional_edges("weather", _after_weather, {"compose": "compose", "policy": "policy"})
    graph.add_edge("policy", "compose")
    graph.add_edge("compose", END)
    return graph.compile()
