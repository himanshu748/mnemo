"""Namespace formatting shared between the Slack surface and the MCP surface,
so a token minted from Slack and a call made from an MCP client land on the
exact same memory store."""
from __future__ import annotations


def user_ns(team_id: str, user_id: str) -> str:
    return "%s:user:%s" % (team_id or "team", user_id or "anon")


def channel_ns(team_id: str, channel_id: str) -> str:
    return "%s:channel:%s" % (team_id or "team", channel_id)
