"""MCP server exposing Mnemo's memory engine to any MCP client (Claude
Desktop, Claude Code, Cursor, ...). Every call is authenticated by a per-user
token (minted in Slack via `/mnemo-token`) so a caller only ever touches their
own private memory - the exact same store their Slack DMs / Assistant thread
write to. No Slack dependency here; `slack_app/` is the only Slack-aware code.

Business logic lives in the plain `do_*` functions so it can be unit-tested
without going through the MCP transport at all; the `@mcp.tool()` wrappers
are thin.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .agent import MemoryAgent
from .client import LLMClient
from .router import get_router
from .tokens import verify

_client = LLMClient()
# get_router() returns the same process-wide instance slack_app.app.build_app()
# uses (same data_dir), so a Slack write and an MCP read never go stale
# relative to each other even though they're built independently.
_router = get_router(_client, data_dir=os.environ.get("MNEMO_DATA_DIR", "data"))

# The SDK's DNS-rebinding guard only allow-lists localhost by default, which
# 421s every real client hitting the public Space URL. Allow-list that host
# explicitly (configurable, since the Space name can change) instead of
# disabling the protection outright.
_PUBLIC_HOST = os.environ.get("MNEMO_PUBLIC_HOST", "himanshukumarjha-mnemo.hf.space")

mcp = FastMCP(
    "mnemo",
    instructions=(
        "Long-term memory shared with the caller's Slack workspace. Every "
        "tool call needs `token` - get one in Slack by running `/mnemo-token`."
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=[_PUBLIC_HOST, "127.0.0.1:*", "localhost:*"],
        allowed_origins=["https://%s" % _PUBLIC_HOST, "http://127.0.0.1:*", "http://localhost:*"],
    ),
)


def _agent_for(token: str) -> Tuple[str, MemoryAgent]:
    ns = verify(token)
    return ns, MemoryAgent(store=_router.store(ns), client=_client)


def do_remember(token: str, text: str, importance: Optional[float] = None) -> dict:
    ns, agent = _agent_for(token)
    agent.remember(text, importance)
    _router.save(ns)
    return {"ok": True, "stats": agent.store.stats()}


def do_recall(token: str, query: str, token_budget: int = 400) -> dict:
    ns, agent = _agent_for(token)
    result = agent.store.budget_retrieve(query, token_budget)
    return {
        "memories": [it.text for it in result["selected"]],
        "tokens_used": result["tokens_used"],
        "compression": round(result["compression"], 3),
    }


def do_chat(token: str, message: str) -> dict:
    ns, agent = _agent_for(token)
    out = agent.chat(message)
    _router.save(ns)
    return out


def do_sleep(token: str) -> dict:
    ns, agent = _agent_for(token)
    report = agent.sleep()
    _router.save(ns)
    return report


@mcp.tool()
def mnemo_remember(token: str, text: str, importance: Optional[float] = None) -> dict:
    """Store a fact in the caller's Mnemo memory - the same memory their Slack account uses."""
    return do_remember(token, text, importance)


@mcp.tool()
def mnemo_recall(token: str, query: str, token_budget: int = 400) -> dict:
    """Recall the caller's memories relevant to `query`, packed into a token budget."""
    return do_recall(token, query, token_budget)


@mcp.tool()
def mnemo_chat(token: str, message: str) -> dict:
    """Chat with the caller's Mnemo memory: retrieves under budget, answers, writes the exchange back."""
    return do_chat(token, message)


@mcp.tool()
def mnemo_sleep(token: str) -> dict:
    """Run consolidation + forgetting on the caller's memory."""
    return do_sleep(token)
