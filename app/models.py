from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Condition(BaseModel):
    field: str
    operator: Literal[">=", ">", "<=", "<", "==", "in", "contains"]
    value: Any


class SOP(BaseModel):
    id: str
    category: str
    title: str
    severity: Severity
    activities: list[str] = Field(default_factory=lambda: ["any"])
    conditions: list[Condition] = Field(default_factory=list)
    condition_mode: Literal["all", "any"] = "all"
    guidance: str
    rationale: str


class Location(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    timezone: str | None = None


class WeatherSnapshot(BaseModel):
    location: Location
    observed_at: str
    target_period: Literal["now", "evening"] = "now"
    temperature_c: float | None = None
    wind_kmh: float | None = None
    precipitation_mm: float | None = None
    precipitation_probability: float | None = None
    uv_index: float | None = None
    weather_code: int | None = None
    precipitation_sum_mm: float | None = None
    wind_gust_kmh: float | None = None
    wind_gust_max_kmh: float | None = None
    source: str = "Open-Meteo"


class Intent(BaseModel):
    activity: str
    target_period: Literal["now", "evening"] = "now"
    vulnerable_group: str | None = None


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    # Context returned by this backend on the preceding turn. This lets a UI
    # preserve a browser chat across an in-process backend reload.
    context_location: Location | None = None
    context_intent: Intent | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    outcome: Literal["matched", "no_policy", "weather_unavailable", "location_needed", "intent_needed"]
    sop_id: str | None = None
    severity: Severity | None = None
    weather: WeatherSnapshot | None = None
    context_location: Location | None = None
    context_intent: Intent | None = None
