"""Glue between Slack and the Mnemo engine.

Pure-Python, no Slack dependency — so it can be unit-tested and self-tested
without slack_bolt installed. The Bolt app (app.py) calls into this.
"""
from __future__ import annotations

from typing import Dict, Optional

from mnemo.client import LLMClient
from mnemo.router import MemoryRouter
from mnemo.agent import MemoryAgent


class SlackMemoryGlue:
    def __init__(self, token_budget: int = 400, data_dir: str = "data",
                 client: Optional[LLMClient] = None):
        self.client = client or LLMClient()
        self.router = MemoryRouter(self.client, data_dir)
        self.token_budget = token_budget

    def _agent(self, ns: str) -> MemoryAgent:
        return MemoryAgent(store=self.router.store(ns), client=self.client,
                           token_budget=self.token_budget)

    def chat(self, ns: str, text: str) -> Dict[str, object]:
        out = self._agent(ns).chat(text)
        self.router.save(ns)
        return out

    def remember(self, ns: str, text: str, importance: Optional[float] = None) -> None:
        self._agent(ns).remember(text, importance)
        self.router.save(ns)

    def recall(self, ns: str, query: str) -> Dict[str, object]:
        return self.router.store(ns).budget_retrieve(query, self.token_budget)

    def sleep(self, ns: str) -> Dict[str, object]:
        report = self._agent(ns).sleep()
        self.router.save(ns)
        return report

    def stats(self, ns: str) -> Dict[str, object]:
        return self.router.store(ns).stats()

    def backend(self) -> str:
        c = self.client
        return ("%s · %s" % (c.provider, c.chat_model)) if c.online else "offline-fallback"
