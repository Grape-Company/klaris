from __future__ import annotations

import hashlib
from collections import OrderedDict
from time import monotonic
from typing import Any


class LRUCache:
    def __init__(self, max_size: int = 128, ttl_seconds: int = 600) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        if monotonic() - ts >= self._ttl_seconds:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (monotonic(), value)

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


def ask_cache_key(question: str, top_k: int) -> str:
    normalized = f"{question.strip().lower()}:{top_k}"
    return hashlib.sha256(normalized.encode()).hexdigest()
