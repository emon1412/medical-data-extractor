"""Tiny in-process cache for PDF extraction results, keyed by content hash.

This is deliberately process-local — no Redis, no external deps. On Cloud Run
each container instance has its own cache; cold starts begin empty. That's fine
for an MVP: the most common dedupe target (the same demo PDF being uploaded
repeatedly during testing) gets cached on the first hit, every subsequent
upload of the same bytes returns instantly without burning OpenAI tokens.

For production scale this would be swapped for a shared cache (Redis,
Memorystore, or a `pdf_extractions` Postgres table keyed by sha256).
"""
from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from typing import Optional

from app.schemas.extraction import PatientExtraction


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _LRUCache:
    def __init__(self, max_size: int = 128) -> None:
        self._store: "OrderedDict[str, PatientExtraction]" = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size

    def get(self, key: str) -> Optional[PatientExtraction]:
        with self._lock:
            value = self._store.get(key)
            if value is None:
                return None
            # Touch (move to most-recent end)
            self._store.move_to_end(key)
            # Return a copy so callers can mutate confidence/source freely
            return value.model_copy()

    def put(self, key: str, value: PatientExtraction) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Module-level singleton — one cache per process.
extraction_cache = _LRUCache(max_size=128)
