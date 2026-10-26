"""
Goldmine AI — Cache Abstraction

Simple in-memory cache with TTL support.
Can be replaced with Redis later without changing the interface.
"""

import time
from typing import Any, Optional
from collections import OrderedDict
import threading


class CacheEntry:
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl


class Cache:
    """
    Thread-safe in-memory cache with TTL and max-size eviction.
    Designed to be swappable with Redis via the same interface.
    """

    def __init__(self, max_size: int = 1000):
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() > entry.expires_at:
                del self._store[key]
                return None
            # Move to end (LRU)
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]
            elif len(self._store) >= self._max_size:
                self._store.popitem(last=False)
            self._store[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def has(self, key: str) -> bool:
        return self.get(key) is not None


# Global cache instance — scoped by key prefix to prevent cross-user leaks
cache = Cache()
