"""MemoryRouter — one persistent MemoryStore per namespace.

In Slack, each user (in a DM/assistant thread) and each channel gets its own
isolated memory, keyed by a namespace string like "T123:user:U456" or
"T123:channel:C789". Stores are lazy-loaded from disk and saved after writes.

Snapshot sync (optional): ephemeral hosts like free HF Spaces lose local disk
on rebuild. Set MNEMO_HF_DATASET (e.g. "user/mnemo-memory") and HF_TOKEN and
every save is mirrored to that private dataset repo; missing local files are
restored from it on first access. Without those env vars this is inert.
"""
from __future__ import annotations

import os
import threading
from typing import Dict, List, Optional

from .client import LLMClient
from .memory import MemoryStore


class _HFSnapshotSync:
    """Fire-and-forget mirror of memory JSON files to a HF dataset repo."""

    def __init__(self) -> None:
        self.repo = os.environ.get("MNEMO_HF_DATASET", "")
        self.enabled = bool(self.repo and os.environ.get("HF_TOKEN"))
        self._ready = False

    def _api(self):
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ["HF_TOKEN"])
        if not self._ready:
            api.create_repo(self.repo, repo_type="dataset", private=True, exist_ok=True)
            self._ready = True
        return api

    def push(self, path: str) -> None:
        if not self.enabled:
            return

        def _upload():
            try:
                self._api().upload_file(
                    path_or_fileobj=path, path_in_repo="memory/" + os.path.basename(path),
                    repo_id=self.repo, repo_type="dataset")
            except Exception as exc:
                print("[mnemo] snapshot push failed:", exc, flush=True)

        threading.Thread(target=_upload, daemon=True).start()

    def pull(self, filename: str, dest: str) -> None:
        if not self.enabled:
            return
        try:
            from huggingface_hub import hf_hub_download
            got = hf_hub_download(self.repo, "memory/" + filename, repo_type="dataset",
                                  token=os.environ["HF_TOKEN"])
            with open(got, "rb") as src, open(dest, "wb") as out:
                out.write(src.read())
            print("[mnemo] restored %s from %s" % (filename, self.repo), flush=True)
        except Exception:
            pass  # nothing snapshotted yet for this namespace


class MemoryRouter:
    def __init__(self, client: Optional[LLMClient] = None, data_dir: str = "data"):
        self.client = client or LLMClient()
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self._stores: Dict[str, MemoryStore] = {}
        self._lock = threading.Lock()
        self._sync = _HFSnapshotSync()

    def _path(self, ns: str) -> str:
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in ns)
        return os.path.join(self.data_dir, safe + ".json")

    def store(self, ns: str) -> MemoryStore:
        with self._lock:
            if ns not in self._stores:
                store = MemoryStore(self.client)
                path = self._path(ns)
                if not os.path.exists(path):
                    self._sync.pull(os.path.basename(path), path)
                if os.path.exists(path):
                    try:
                        store.load(path)
                    except Exception:
                        pass  # corrupt/old file -> start fresh rather than crash
                self._stores[ns] = store
            return self._stores[ns]

    def save(self, ns: str) -> None:
        path = self._path(ns)
        self.store(ns).save(path)
        self._sync.push(path)

    def namespaces(self) -> List[str]:
        return list(self._stores.keys())


# Process-wide singleton per data_dir. The Slack bot (background thread) and
# the MCP server (uvicorn's threadpool) are two independent callers in the
# same process; if each built its own MemoryRouter they'd keep two separate
# in-memory caches and go stale relative to each other's writes even though
# both persist to the same directory. get_router() ensures every in-process
# caller for a given data_dir shares one cache (and one lock).
_ROUTERS: Dict[str, "MemoryRouter"] = {}
_registry_lock = threading.Lock()


def get_router(client: Optional[LLMClient] = None, data_dir: str = "data") -> "MemoryRouter":
    key = os.path.abspath(data_dir)
    with _registry_lock:
        if key not in _ROUTERS:
            _ROUTERS[key] = MemoryRouter(client, data_dir)
        return _ROUTERS[key]
