from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from app.config import POLICY_PATH
from app.models import SOP, Severity, WeatherSnapshot

SEVERITY_RANK = {Severity.LOW: 1, Severity.MODERATE: 2, Severity.HIGH: 3, Severity.CRITICAL: 4}


@lru_cache(maxsize=1)
def load_sops() -> list[SOP]:
    """Load policies from YAML, keeping policy changes out of graph control flow."""
    with POLICY_PATH.open() as policy_file:
        data = yaml.safe_load(policy_file)
    return [SOP.model_validate(item) for item in data["sops"]]


def reload_sops() -> None:
    load_sops.cache_clear()


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if actual is None:
        return False
    if operator == ">=": return actual >= expected
    if operator == ">": return actual > expected
    if operator == "<=": return actual <= expected
    if operator == "<": return actual < expected
    if operator == "==": return actual == expected
    if operator == "in": return actual in expected
    if operator == "contains": return expected in actual
    raise ValueError(f"Unsupported policy operator: {operator}")


def match_sops(weather: WeatherSnapshot, activity: str, vulnerable_group: str | None) -> list[SOP]:
    """Evaluate a declarative condition DSL; highest severity wins deterministically."""
    facts = weather.model_dump()
    facts["activity"] = activity
    facts["vulnerable_group"] = vulnerable_group
    matched: list[SOP] = []
    for sop in load_sops():
        if "any" not in sop.activities and activity not in sop.activities:
            continue
        checks = [_compare(facts.get(c.field), c.operator, c.value) for c in sop.conditions]
        applies = all(checks) if sop.condition_mode == "all" else any(checks)
        if applies:
            matched.append(sop)
    # At equal severity, a broad all-activity hazard wins over an activity
    # detail, so the response leads with the wider safety risk.
    return sorted(
        matched,
        key=lambda sop: (SEVERITY_RANK[sop.severity], "any" in sop.activities),
        reverse=True,
    )
