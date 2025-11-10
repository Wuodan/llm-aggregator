from __future__ import annotations

import asyncio
import time
from typing import Dict, List

from ..models import ModelKey, ModelInfo, EnrichedModel


class ModelStore:
    """In-memory state and enrichment queue for models.

    Responsibilities:
    - Track the current set of discovered models.
    - Track enriched metadata for those models.
    - Maintain a queue of models that still need enrichment.
    - Provide snapshots for the /api/models endpoint.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._models: Dict[ModelKey, ModelInfo] = {}
        self._enriched: Dict[ModelKey, EnrichedModel] = {}
        self._queue: asyncio.Queue[ModelInfo] = asyncio.Queue()
        self._queued_keys: set[ModelKey] = set()
        self._last_update_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def last_update_ts(self) -> float:
        return self._last_update_ts

    async def update_models(self, new_models: List[ModelInfo]) -> None:
        """Replace the current model set with ``new_models``.

        - Removes vanished models from both models and enriched.
        - Adds newly discovered models and enqueues them for enrichment.
        - Keeps existing models as-is (no implicit re-enqueue).

        This method is intended to be called by the periodic refresh loop.
        """
        async with self._lock:
            new_by_key = {m.key: m for m in new_models}

            # Drop models that vanished
            removed_keys = set(self._models.keys()) - set(new_by_key.keys())
            for key in removed_keys:
                self._models.pop(key, None)
                self._enriched.pop(key, None)
                self._queued_keys.discard(key)

            # Add or update models
            for key, m in new_by_key.items():
                if key in self._models:
                    # Update raw info in case something changed
                    self._models[key] = m
                else:
                    # New model: store and enqueue for enrichment once
                    self._models[key] = m
                    await self._enqueue_no_duplicate(m)

            self._last_update_ts = time.time()

    async def get_snapshot(self) -> Dict[str, List[dict]]:
        """Return a snapshot compatible with the public /api/models shape.

        Structure:
        {
          "models":   [ ... ],
          "enriched": [ ... ]
        }
        """
        async with self._lock:
            models_list = [m.to_api_dict() for m in self._models.values()]

            # Only include enriched entries that still have a backing model
            enriched_list = [
                em.to_api_dict()
                for key, em in self._enriched.items()
                if key in self._models
            ]

        # Sorting outside the lock: stable, deterministic output
        models_list.sort(key=lambda m: (m.get("server_port", 0), str(m.get("id", ""))))
        enriched_list.sort(
            key=lambda e: (e.get("server_port", 0), str(e.get("model", "")))
        )

        return {
            "models": models_list,
            "enriched": enriched_list,
        }

    async def get_enrichment_batch(self, max_batch_size: int) -> List[ModelInfo]:
        """Pop up to ``max_batch_size`` models from the queue for enrichment.

        Non-blocking: stops when the queue is empty.
        """
        if max_batch_size <= 0:
            return []

        batch: List[ModelInfo] = []
        for _ in range(max_batch_size):
            try:
                m = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                # Mark as no longer queued so it can be re-queued later if needed
                self._queued_keys.discard(m.key)
                batch.append(m)

        return batch

    async def apply_enrichment(self, enriched_models: List[EnrichedModel]) -> None:
        """Merge successful enrichment results into the store.

        Unknown keys are ignored (models might have vanished between request and response).
        """
        if not enriched_models:
            return

        async with self._lock:
            for em in enriched_models:
                if em.key in self._models:
                    self._enriched[em.key] = em

    async def requeue_models(self, models: List[ModelInfo]) -> None:
        """Re-enqueue models for enrichment after a failed attempt.

        Only models that still exist in the store are re-queued.
        Duplicates are avoided via the same mechanism as initial enqueue.
        """
        if not models:
            return

        async with self._lock:
            for m in models:
                # Only requeue if model is still active
                if m.key in self._models:
                    await self._enqueue_no_duplicate(m)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _enqueue_no_duplicate(self, model: ModelInfo) -> None:
        """Enqueue model for enrichment if not already queued.

        Must be called with the lock held.
        """
        if model.key in self._queued_keys:
            return
        await self._queue.put(model)
        self._queued_keys.add(model.key)
