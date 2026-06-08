"""MemoryRouter — one persistent MemoryStore per namespace.

In Slack, each user (in a DM/assistant thread) and each channel gets its own
isolated memory, keyed by a namespace string like "T123:user:U456" or
"T123:channel:C789". Stores are lazy-loaded from disk and saved after writes.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from .client import LLMClient
from .memory import MemoryStore


class MemoryRouter:
    def __init__(self, client: Optional[LLMClient] = None, data_dir: str = "data"):
        self.client = client or LLMClient()
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self._stores: Dict[str, MemoryStore] = {}

    def _path(self, ns: str) -> str:
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in ns)
        return os.path.join(self.data_dir, safe + ".json")

    def store(self, ns: str) -> MemoryStore:
        if ns not in self._stores:
            store = MemoryStore(self.client)
            path = self._path(ns)
            if os.path.exists(path):
                try:
                    store.load(path)
                except Exception:
                    pass  # corrupt/old file -> start fresh rather than crash
            self._stores[ns] = store
        return self._stores[ns]

    def save(self, ns: str) -> None:
        self.store(ns).save(self._path(ns))

    def namespaces(self) -> List[str]:
        return list(self._stores.keys())
