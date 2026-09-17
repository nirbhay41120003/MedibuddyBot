import json

import pytest

import app.intent as intent_module


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self.content)}}]}


class FakeClient:
    calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        type(self).calls += 1
        return FakeResponse({"activity": "cycling", "target_period": "now", "vulnerable_group": None})


@pytest.mark.asyncio
async def test_llm_classifies_task_requests_even_when_fallback_knows_activity(monkeypatch):
    FakeClient.calls = 0
    monkeypatch.setattr(intent_module, "USE_GROQ_INTENT", True)
    monkeypatch.setattr(intent_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(intent_module.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await intent_module.extract_intent_with_optional_llm("Can I cycle in Bhopal today?")

    assert result.activity == "cycling"
    assert FakeClient.calls == 1


@pytest.mark.asyncio
async def test_llm_is_skipped_for_greetings(monkeypatch):
    FakeClient.calls = 0
    monkeypatch.setattr(intent_module, "USE_GROQ_INTENT", True)
    monkeypatch.setattr(intent_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(intent_module.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await intent_module.extract_intent_with_optional_llm("hi")

    assert result.activity == "unknown"
    assert FakeClient.calls == 0


@pytest.mark.asyncio
async def test_llm_handles_ambiguous_task_request_with_constrained_schema(monkeypatch):
    FakeClient.calls = 0
    monkeypatch.setattr(intent_module, "USE_GROQ_INTENT", True)
    monkeypatch.setattr(intent_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(intent_module.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await intent_module.extract_intent_with_optional_llm("Would a strenuous outing be safe in Pune today?")

    assert result.activity == "cycling"
    assert FakeClient.calls == 1


@pytest.mark.asyncio
async def test_explicit_local_correction_cannot_be_reversed_by_llm(monkeypatch):
    monkeypatch.setattr(intent_module, "USE_GROQ_INTENT", True)
    monkeypatch.setattr(intent_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(intent_module.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await intent_module.extract_intent_with_optional_llm("Can I go not cycling but camping in Lucknow?")

    assert result.activity == "camping"


def test_tomorrow_is_a_supported_target_period():
    result = intent_module.extract_intent("Can I go camping in Lucknow tomorrow?")
    assert result.target_period == "tomorrow"


@pytest.mark.asyncio
async def test_invalid_llm_activity_falls_back_to_deterministic_unknown(monkeypatch):
    class InvalidClient(FakeClient):
        async def post(self, *args, **kwargs):
            return FakeResponse({"activity": "invented_activity", "target_period": "now", "vulnerable_group": None})

    monkeypatch.setattr(intent_module, "USE_GROQ_INTENT", True)
    monkeypatch.setattr(intent_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(intent_module.httpx, "AsyncClient", lambda **kwargs: InvalidClient())

    result = await intent_module.extract_intent_with_optional_llm("Can I do something outside in Pune today?")

    assert result.activity == "unknown"
