"""LLM client for Mnemo — provider-agnostic (OpenAI-compatible).

Works with any OpenAI-compatible chat + embeddings API. Built-in presets:
  - gemini  (Google AI Studio OpenAI-compatible endpoint; free tier, India-OK)
  - openai
  - qwen    (Alibaba DashScope International)

Selection order (per field): explicit arg > LLM_* env > provider preset.
Provider is chosen via LLM_PROVIDER, else auto-detected from whichever API key
is present, else "offline". With no key it falls back to a deterministic
offline implementation so the system stays demoable and testable.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Dict, List, Optional

PROVIDERS: Dict[str, Dict[str, object]] = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "chat_model": "gemini-2.5-flash",
        "embed_model": "gemini-embedding-001",
        "key_env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "chat_model": "gpt-4o-mini",
        "embed_model": "text-embedding-3-small",
        "key_env": ["OPENAI_API_KEY"],
    },
    "qwen": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "chat_model": "qwen-plus",
        "embed_model": "text-embedding-v3",
        "key_env": ["QWEN_API_KEY", "DASHSCOPE_API_KEY"],
    },
}
OFFLINE_EMBED_DIM = 256

_WORD = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _WORD.findall(text.lower())


def _detect_provider() -> Optional[str]:
    explicit = os.environ.get("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    for name, cfg in PROVIDERS.items():
        for env_name in cfg["key_env"]:  # type: ignore[index]
            if os.environ.get(env_name):
                return name
    return None


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> None:
        self.provider = (provider or _detect_provider() or "offline").lower()
        preset = PROVIDERS.get(self.provider, {})

        key = api_key or os.environ.get("LLM_API_KEY")
        if not key:
            for env_name in preset.get("key_env", []):  # type: ignore[union-attr]
                key = key or os.environ.get(env_name)
        self.api_key = key
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL")
                         or preset.get("base_url", "")).rstrip("/")  # type: ignore[union-attr]
        self.chat_model = (chat_model or os.environ.get("LLM_CHAT_MODEL")
                           or preset.get("chat_model", "offline-model"))
        self.embed_model = (embed_model or os.environ.get("LLM_EMBED_MODEL")
                            or preset.get("embed_model", "offline-embed"))
        self.online = bool(self.api_key and self.base_url)

    # ----------------------------- chat -----------------------------
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 512) -> str:
        if self.online:
            try:
                return self._chat_remote(messages, temperature, max_tokens)
            except Exception as exc:  # graceful: never crash the agent loop
                return "[llm-error:%s] %s" % (exc, self._chat_offline(messages))
        return self._chat_offline(messages)

    def _chat_remote(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        import requests  # lazy import; honors HTTPS_PROXY

        url = "%s/chat/completions" % self.base_url
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": "Bearer %s" % self.api_key, "Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        message = resp.json()["choices"][0].get("message", {})
        return (message.get("content") or "").strip()

    def _chat_offline(self, messages: List[Dict[str, str]]) -> str:
        """Grounded fallback so the pipeline runs without a key. Two modes:
        - summarize (consolidation): compress the user-supplied notes.
        - answer: reply from whichever retrieved memory best overlaps the
          question (right retrieval -> right answer; none -> "I don't recall")."""
        system = ""
        question = ""
        for m in messages:
            if m.get("role") == "user":
                question = m.get("content", "")
            elif m.get("role") == "system":
                system = m.get("content", "")
        if "summarize" in system.lower():
            return self._summarize_offline(question)
        q_terms = set(_tokenize(question))
        best_line, best_overlap = "", 0
        for line in system.splitlines():
            clean = line.lstrip("0123456789.-) ").strip()
            if not clean:
                continue
            overlap = len(q_terms & set(_tokenize(clean)))
            if overlap > best_overlap:
                best_overlap, best_line = overlap, clean
        if best_overlap == 0:
            return "I don't have a memory relevant to that yet."
        return "Based on what I remember: %s" % best_line

    @staticmethod
    def _summarize_offline(notes: str) -> str:
        """Compress related notes by factoring out their common word-prefix.
        Real models write a proper summary; this keeps the offline demo honest."""
        lines = [ln.lstrip("-*0123456789.) ").strip() for ln in notes.splitlines() if ln.strip()]
        if not lines:
            return "(nothing to summarize)"
        if len(lines) == 1:
            return lines[0]
        splits = [ln.split() for ln in lines]
        prefix: List[str] = []
        for col in zip(*splits):
            if all(w == col[0] for w in col):
                prefix.append(col[0])
            else:
                break
        plen = len(prefix)
        remainders = [" ".join(s[plen:]).rstrip(".") for s in splits]
        remainders = [r for r in remainders if r]
        if prefix and remainders:
            return ("%s %s." % (" ".join(prefix), ", ".join(remainders))).strip()
        return "; ".join(lines)

    # --------------------------- embeddings --------------------------
    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.online:
            try:
                return self._embed_remote(texts)
            except Exception:
                return [self._embed_offline(t) for t in texts]
        return [self._embed_offline(t) for t in texts]

    def _embed_remote(self, texts: List[str]) -> List[List[float]]:
        import requests

        url = "%s/embeddings" % self.base_url
        headers = {"Authorization": "Bearer %s" % self.api_key, "Content-Type": "application/json"}
        resp = requests.post(url, json={"model": self.embed_model, "input": texts}, headers=headers, timeout=60)
        resp.raise_for_status()
        return [row["embedding"] for row in resp.json()["data"]]

    def _embed_offline(self, text: str) -> List[float]:
        """Deterministic hashed bag-of-words embedding (L2-normalized). Not
        semantic, but stable and good enough to exercise cosine retrieval."""
        vec = [0.0] * OFFLINE_EMBED_DIM
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % OFFLINE_EMBED_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]


# Backward-compatible alias (Mnemo started Qwen-specific).
QwenClient = LLMClient
