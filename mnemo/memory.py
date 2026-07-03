"""The Mnemo memory store: episodic + semantic memories, time decay with
forgetting, sleep-time consolidation, and budget-aware retrieval.

Design goals
------------
* Budget-aware retrieval: return the *minimal critical* set of memories that
  fits a hard token budget, ranked by relevance modulated by importance.
* Forgetting: low-value episodic memories decay over time and are pruned, so
  the store doesn't grow without bound.
* Consolidation ("sleep"): clusters of related episodic memories are summarized
  into durable semantic memories via the LLM, compressing many raw events into
  a few high-value facts.
"""
from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from .client import QwenClient

EPISODIC = "episodic"
SEMANTIC = "semantic"


def _now() -> float:
    return time.time()


def _est_tokens(text: str) -> int:
    # ~4 chars/token heuristic, min 1.
    return max(1, len(text) // 4)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class MemoryItem:
    text: str
    kind: str = EPISODIC
    importance: float = 0.5          # 0..1 caller/heuristic supplied salience
    embedding: List[float] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=_now)
    last_access: float = field(default_factory=_now)
    access_count: int = 0
    source_ids: List[str] = field(default_factory=list)  # for consolidated memories

    def retention(self, now: Optional[float] = None, half_life_days: float = 7.0) -> float:
        """Dynamic keep-score in [0, ~1.x]. Importance decays with age but is
        boosted by access frequency; semantic memories decay much slower."""
        now = now or _now()
        age_days = max(0.0, (now - self.created_at) / 86400.0)
        hl = half_life_days * (6.0 if self.kind == SEMANTIC else 1.0)
        decay = 0.5 ** (age_days / hl)
        freq_boost = 1.0 + math.log1p(self.access_count) * 0.15
        return self.importance * decay * freq_boost

    def tokens(self) -> int:
        return _est_tokens(self.text)


class MemoryStore:
    def __init__(self, client: Optional[QwenClient] = None, half_life_days: float = 7.0):
        self.client = client or QwenClient()
        self.items: Dict[str, MemoryItem] = {}
        self.half_life_days = half_life_days

    # ------------------------------ writes ------------------------------
    def add(self, text: str, kind: str = EPISODIC, importance: float = 0.5,
            source_ids: Optional[List[str]] = None) -> MemoryItem:
        emb = self.client.embed([text])[0]
        item = MemoryItem(text=text, kind=kind, importance=_clamp(importance),
                          embedding=emb, source_ids=source_ids or [])
        self.items[item.id] = item
        return item

    def remove(self, item_id: str) -> None:
        self.items.pop(item_id, None)

    # ------------------------------ reads -------------------------------
    def _rank(self, query: str) -> List[Tuple[float, MemoryItem]]:
        q = self.client.embed([query])[0]
        scored: List[Tuple[float, MemoryItem]] = []
        for item in self.items.values():
            rel = _cosine(q, item.embedding)
            # relevance modulated by importance (so a slightly-less-similar but
            # high-importance fact can still win) and a small recency nudge.
            value = rel * (0.6 + 0.4 * item.importance)
            scored.append((value, item))
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored

    def search(self, query: str, k: int = 5) -> List[MemoryItem]:
        return [it for _, it in self._rank(query)[:k]]

    def budget_retrieve(self, query: str, token_budget: int,
                        min_relevance: float = 0.0) -> Dict[str, object]:
        """Greedily select the highest-value memories that fit token_budget.
        Returns the selected items plus accounting so callers can prove the
        savings vs. dumping the whole store into context."""
        ranked = self._rank(query)
        selected: List[MemoryItem] = []
        used = 0
        for value, item in ranked:
            if value < min_relevance:
                continue
            cost = item.tokens()
            if used + cost > token_budget:
                continue
            selected.append(item)
            used += cost
        # mark access (drives frequency boost + recency)
        now = _now()
        for it in selected:
            it.access_count += 1
            it.last_access = now
        full_tokens = sum(it.tokens() for it in self.items.values())
        return {
            "selected": selected,
            "tokens_used": used,
            "token_budget": token_budget,
            "full_context_tokens": full_tokens,
            "compression": (1.0 - used / full_tokens) if full_tokens else 0.0,
        }

    # --------------------------- forgetting -----------------------------
    def decay_and_prune(self, keep_threshold: float = 0.05) -> List[str]:
        """Drop episodic memories whose retention has fallen below threshold.
        Semantic memories are effectively never pruned here (slow half-life)."""
        now = _now()
        pruned: List[str] = []
        for item in list(self.items.values()):
            if item.kind == SEMANTIC:
                continue
            if item.retention(now, self.half_life_days) < keep_threshold:
                pruned.append(item.id)
                del self.items[item.id]
        return pruned

    # -------------------------- consolidation ---------------------------
    def _classify_cluster(self, texts: List[str]) -> str:
        """Ask the LLM whether related notes agree or contradict each other.
        Returns "agree" or "conflict". Cosine similarity alone can't tell these
        apart - "standup is at 9" and "standup is at 9:30" are topically
        near-identical but factually contradictory."""
        messages = [
            {"role": "system", "content": (
                "You will see 2+ short related notes. Reply with exactly one "
                "word: 'agree' if they are consistent (same fact, a paraphrase, "
                "or one refining another), or 'conflict' if they contradict "
                "each other (different values for the same thing - a time, "
                "date, person, place, or decision).")},
            {"role": "user", "content": "\n".join("- %s" % t for t in texts)},
        ]
        verdict = self.client.chat(messages, temperature=0.0, max_tokens=5).strip().lower()
        return "conflict" if "conflict" in verdict else "agree"

    def consolidate(self, similarity_threshold: float = 0.55,
                    min_cluster: int = 2, max_clusters: int = 5
                    ) -> Tuple[List[MemoryItem], List[Dict[str, object]]]:
        """Sleep-time pass: cluster related episodic memories. Agreeing
        clusters are summarized into one durable semantic memory via the LLM;
        source episodics are demoted (importance lowered) so consolidated
        knowledge dominates retrieval and the raw events eventually decay away.
        Conflicting clusters are left alone and reported instead of silently
        merged, so a caller (e.g. the Slack bot) can flag them to the team."""
        episodics = [it for it in self.items.values() if it.kind == EPISODIC]
        used: set = set()
        clusters: List[List[MemoryItem]] = []
        for anchor in episodics:
            if anchor.id in used:
                continue
            cluster = [anchor]
            used.add(anchor.id)
            for other in episodics:
                if other.id in used:
                    continue
                if _cosine(anchor.embedding, other.embedding) >= similarity_threshold:
                    cluster.append(other)
                    used.add(other.id)
            if len(cluster) >= min_cluster:
                clusters.append(cluster)
            if len(clusters) >= max_clusters:
                break

        new_semantic: List[MemoryItem] = []
        conflicts: List[Dict[str, object]] = []
        for cluster in clusters:
            texts = [c.text for c in cluster]
            if self._classify_cluster(texts) == "conflict":
                conflicts.append({
                    "texts": texts,
                    "ids": [c.id for c in cluster],
                })
                continue
            joined = "\n".join("- %s" % t for t in texts)
            messages = [
                {"role": "system", "content": "Summarize the related notes below into ONE concise, durable fact. Reply with the fact only."},
                {"role": "user", "content": joined},
            ]
            summary = self.client.chat(messages, temperature=0.2, max_tokens=120).strip()
            if summary.lower().startswith("based on what i remember:"):
                summary = summary.split(":", 1)[1].strip()
            importance = min(1.0, max(c.importance for c in cluster) + 0.1)
            sem = self.add(summary, kind=SEMANTIC, importance=importance,
                           source_ids=[c.id for c in cluster])
            for c in cluster:
                c.importance = _clamp(c.importance * 0.4)  # demote raw events
            new_semantic.append(sem)
        return new_semantic, conflicts

    # ------------------------------ stats -------------------------------
    def stats(self) -> Dict[str, object]:
        episodic = [it for it in self.items.values() if it.kind == EPISODIC]
        semantic = [it for it in self.items.values() if it.kind == SEMANTIC]
        return {
            "total": len(self.items),
            "episodic": len(episodic),
            "semantic": len(semantic),
            "total_tokens": sum(it.tokens() for it in self.items.values()),
        }

    # --------------------------- persistence ----------------------------
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([asdict(it) for it in self.items.values()], fh)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            rows = json.load(fh)
        self.items = {}
        for row in rows:
            item = MemoryItem(**row)
            self.items[item.id] = item


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
