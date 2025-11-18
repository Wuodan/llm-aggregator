from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class CacheEntry:
    value: str | None
    stored_at: float


class WebsiteInfoCache:
    """Simple in-memory TTL cache specialised for website markdown."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._entries: Dict[Tuple[str, str], CacheEntry] = {}

    async def get(self, source: str, model_id: str) -> tuple[bool, str | None]:
        """Return (hit, value) for a cache lookup."""
        async with self._lock:
            entry = self._entries.get((source, model_id))
            if entry is None:
                return False, None
            if self._is_expired(entry):
                self._entries.pop((source, model_id), None)
                return False, None
            return True, entry.value

    async def set(self, source: str, model_id: str, value: str | None) -> None:
        """Store a cache value, even when the value is None."""
        async with self._lock:
            self._entries[(source, model_id)] = CacheEntry(
                value=value,
                stored_at=time.time(),
            )

    def _is_expired(self, entry: CacheEntry) -> bool:
        return (time.time() - entry.stored_at) > self._ttl
