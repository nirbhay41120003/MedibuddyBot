from __future__ import annotations

from collections import defaultdict

from fastapi import FastAPI

from app.graph import build_graph
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Weather Advisory Support Bot")
graph = build_graph()
sessions: dict[str, dict] = defaultdict(dict)


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    prior = sessions[request.session_id]
    remembered_location = prior.get("location") or request.context_location
    remembered_intent = prior.get("intent") or request.context_intent
    result = await graph.ainvoke({
        "message": request.message,
        "remembered_location": remembered_location,
        "remembered_intent": remembered_intent,
    })
    if result.get("location"):
        prior["location"] = result["location"]
    # Unknown/greeting messages must not erase a useful previous activity.
    if result.get("intent") and result["intent"].activity != "unknown":
        prior["intent"] = result["intent"]
    context_location = prior.get("location") or request.context_location
    context_intent = prior.get("intent") or request.context_intent
    return ChatResponse(
        session_id=request.session_id,
        reply=result["reply"], outcome=result["outcome"],
        sop_id=result.get("selected_sop").id if result.get("selected_sop") else None,
        severity=result.get("selected_sop").severity if result.get("selected_sop") else None,
        weather=result.get("weather"),
        context_location=context_location,
        context_intent=context_intent,
    )
