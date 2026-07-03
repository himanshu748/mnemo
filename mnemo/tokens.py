"""Stateless MCP auth tokens binding a caller to their Slack private memory.

Minted in Slack via `/mnemo-token`. Format: "<team_id>.<user_id>.<sig>", where
sig = HMAC-SHA256(MNEMO_TOKEN_SECRET, "team_id:user_id")[:16 hex]. Verifying
just recomputes the HMAC - no token storage or lookup table needed, so any
Space replica can verify a token minted anywhere else.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from .namespace import user_ns


def _secret() -> bytes:
    secret = os.environ.get("MNEMO_TOKEN_SECRET")
    if not secret:
        raise RuntimeError("MNEMO_TOKEN_SECRET is not set - cannot mint or verify MCP tokens")
    return secret.encode("utf-8")


def _sign(team_id: str, user_id: str) -> str:
    msg = "%s:%s" % (team_id, user_id)
    return hmac.new(_secret(), msg.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def mint(team_id: str, user_id: str) -> str:
    return "%s.%s.%s" % (team_id, user_id, _sign(team_id, user_id))


def verify(token: str) -> str:
    """Returns the caller's private namespace, or raises ValueError."""
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    team_id, user_id, sig = parts
    if not hmac.compare_digest(sig, _sign(team_id, user_id)):
        raise ValueError("invalid token")
    return user_ns(team_id, user_id)
