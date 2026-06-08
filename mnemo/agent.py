"""MemoryAgent: a thin conversational loop wired to the Mnemo store.

On each turn it (1) retrieves the minimal critical memory set within a token
budget, (2) asks Qwen with only that context, (3) writes the new exchange back
as an episodic memory. Periodically the caller runs sleep() to consolidate +
forget.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .client import QwenClient
from .memory import MemoryStore, EPISODIC

SYSTEM_PREAMBLE = (
    "You are a helpful assistant with long-term memory. Answer the user using "
    "ONLY the memories below when relevant. If the memories don't cover it, say "
    "you don't recall. Be concise.\n\nMemories:\n"
)


def estimate_importance(text: str) -> float:
    """Cheap heuristic salience: longer, fact-shaped, or preference/identity
    statements score higher. Real deployments can swap in an LLM scorer."""
    t = text.lower()
    score = 0.45
    if any(k in t for k in ("my name", "i am", "i'm", "i live", "i work", "i prefer",
                             "remember", "favorite", "favourite", "birthday", "allergic",
                             "deadline", "password", "email", "phone")):
        score += 0.3
    if re.search(r"\d", t):
        score += 0.1
    if len(text) > 80:
        score += 0.05
    return max(0.0, min(1.0, score))


class MemoryAgent:
    def __init__(self, store: Optional[MemoryStore] = None, client: Optional[QwenClient] = None,
                 token_budget: int = 256):
        self.client = client or QwenClient()
        self.store = store or MemoryStore(self.client)
        self.token_budget = token_budget

    def remember(self, text: str, importance: Optional[float] = None) -> None:
        self.store.add(text, kind=EPISODIC,
                       importance=importance if importance is not None else estimate_importance(text))

    def chat(self, user_message: str, token_budget: Optional[int] = None,
             write_back: bool = True) -> Dict[str, object]:
        budget = token_budget or self.token_budget
        retrieval = self.store.budget_retrieve(user_message, budget)
        selected = retrieval["selected"]
        context = "\n".join("%d. %s" % (i + 1, it.text) for i, it in enumerate(selected))
        messages = [
            {"role": "system", "content": SYSTEM_PREAMBLE + (context or "(none)")},
            {"role": "user", "content": user_message},
        ]
        reply = self.client.chat(messages)
        if write_back:
            self.remember(user_message)
        return {
            "reply": reply,
            "used_memories": [it.text for it in selected],
            "tokens_used": retrieval["tokens_used"],
            "token_budget": budget,
            "full_context_tokens": retrieval["full_context_tokens"],
            "compression": retrieval["compression"],
        }

    def sleep(self) -> Dict[str, object]:
        """Run a consolidation + forgetting pass (call between sessions)."""
        before = self.store.stats()
        new_semantic = self.store.consolidate()
        pruned = self.store.decay_and_prune()
        after = self.store.stats()
        return {
            "before": before,
            "after": after,
            "consolidated": [s.text for s in new_semantic],
            "pruned_count": len(pruned),
        }
