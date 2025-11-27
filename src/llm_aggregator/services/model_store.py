from __future__ import annotations

import asyncio
import time
from typing import Dict, List

from ..models import Model, ModelKey, model_key, public_model_dict


class ModelStore:
    """In-memory state and enrichment queue for models.

    Responsibilities:
    - Track the current set of discovered models.
    - Maintain a queue of models that still need enrichment.
    - Provide snapshots for the public /v1/models endpoint.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._models: Dict[ModelKey, Model] = {}
        self._queue: asyncio.Queue[Model] = asyncio.Queue()
        self._queued_keys: set[ModelKey] = set()
        self._last_update_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def last_update_ts(self) -> float:
        return self._last_update_ts

    async def update_models(self, new_models: List[Model]) -> None:
        """Replace the current model set with ``new_models``.

        - Removes vanished models from both models and enriched.
        - Adds newly discovered models and enqueues them for enrichment.
        - Keeps existing models as-is (no implicit re-enqueue).

        This method is intended to be called by the periodic fetch loop.
        """
        async with self._lock:
            new_by_key = {model_key(m): m for m in new_models}

            # Drop models that vanished
            removed_keys = set(self._models.keys()) - set(new_by_key.keys())
            for key in removed_keys:
                self._models.pop(key, None)
                self._queued_keys.discard(key)

            # Add or update models
            for key, m in new_by_key.items():
                if key in self._models:
                    existing = self._models[key]
                    if self._provider_changed(existing, m):
                        # Provider metadata changed -> replace and re-enqueue.
                        self._models.pop(key, None)
                        self._queued_keys.discard(key)
                        self._models[key] = m
                        await self._enqueue_no_duplicate(m)
                    else:
                        # Provider unchanged: keep existing (including enrichment).
                        continue
                else:
                    # New model: store and enqueue for enrichment once
                    self._models[key] = m
                    await self._enqueue_no_duplicate(m)

            self._last_update_ts = time.time()

    async def get_snapshot(self) -> List[dict]:
        """Return snapshot entries for the public /v1/models response."""
        async with self._lock:
            models = list(self._models.values())
            models.sort(
                key=lambda m: (
                    m.key.provider_name,
                    m.key.id.lower(),
                )
            )
            entries = [public_model_dict(model) for model in models]

            return entries

    async def get_enrichment_batch(self, max_batch_size: int) -> List[Model]:
        """Pop up to ``max_batch_size`` models from the queue for enrichment.

        Non-blocking: stops when the queue is empty.
        """
        if max_batch_size <= 0:
            return []

        batch: List[Model] = []
        for _ in range(max_batch_size):
            try:
                m = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                # Mark as no longer queued so it can be re-queued later if needed
                self._queued_keys.discard(model_key(m))
                batch.append(m)

        return batch

    async def apply_enrichment(self, models: List[Model]) -> None:
        """No-op hook to keep API compatibility; models are already mutated in place."""
        if not models:
            return
        async with self._lock:
            for m in models:
                key = model_key(m)
                if key in self._models:
                    self._models[key] = m

    async def requeue_models(self, models: List[Model]) -> None:
        """Re-enqueue models for enrichment after a failed attempt.

        Only models that still exist in the store are re-queued.
        Duplicates are avoided via the same mechanism as initial enqueue.
        """
        if not models:
            return

        async with self._lock:
            for m in models:
                # Only requeue if model is still active
                if model_key(m) in self._models:
                    await self._enqueue_no_duplicate(m)

    async def clear(self) -> None:
        """Completely reset the in-memory store and queues."""
        async with self._lock:
            self._models.clear()
            self._queued_keys.clear()
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._last_update_ts = 0.0


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _enqueue_no_duplicate(self, model: Model) -> None:
        """Enqueue model for enrichment if not already queued.

        Must be called with the lock held.
        """
        key = model_key(model)
        if key in self._queued_keys:
            return
        await self._queue.put(model)
        self._queued_keys.add(key)

    @staticmethod
    def _provider_changed(existing: Model, incoming: Model) -> bool:
        """Return True if provider-sourced meta fields differ."""
        # Compare meta fields supplied by provider (incoming.meta entries).
        for mk, mv in incoming.meta.items():
            if existing.meta.get(mk) != mv:
                return True
        return False
