"""FastAPI surface for Mnemo — the deployable backend (this is what runs on
Alibaba Cloud for the hackathon's deployment-proof requirement).

Run locally:
    uvicorn mnemo.api:app --reload --port 8000

Endpoints:
    POST /chat          {"message": "...", "token_budget": 256}
    POST /remember      {"text": "...", "importance": 0.8}
    POST /sleep         -> run consolidation + forgetting
    GET  /memories      -> list current memories
    GET  /stats         -> store stats + which model backend is active
    GET  /healthz       -> liveness
"""
from __future__ import annotations

from typing import List, Optional

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except Exception as exc:  # pragma: no cover - only needed for the server
    raise SystemExit("FastAPI/pydantic not installed. `pip install -r requirements.txt`") from exc

from .agent import MemoryAgent
from .client import QwenClient

client = QwenClient()
agent = MemoryAgent(client=client)
app = FastAPI(title="Mnemo", version="0.1.0",
              description="Self-curating memory engine for Qwen agents")


class ChatIn(BaseModel):
    message: str
    token_budget: Optional[int] = None


class RememberIn(BaseModel):
    text: str
    importance: Optional[float] = None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/stats")
def stats():
    s = agent.store.stats()
    s["backend"] = "qwen-online" if client.online else "offline-fallback"
    s["chat_model"] = client.chat_model
    return s


@app.post("/chat")
def chat(body: ChatIn):
    return agent.chat(body.message, token_budget=body.token_budget)


@app.post("/remember")
def remember(body: RememberIn):
    agent.remember(body.text, importance=body.importance)
    return {"ok": True, "stats": agent.store.stats()}


@app.post("/sleep")
def sleep():
    return agent.sleep()


@app.get("/memories")
def memories():
    return [
        {"id": it.id, "kind": it.kind, "importance": round(it.importance, 3),
         "access_count": it.access_count, "text": it.text}
        for it in agent.store.items.values()
    ]
