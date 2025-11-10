from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from ..config import get_settings
from ..models import ModelInfo, EnrichedModel
from .model_store import ModelStore
from .model_sources import gather_models
from .brain_client import enrich_batch


class BackgroundTasksManager:
    """Manage background refresh + enrichment loops.

    Usage (wired from FastAPI lifespan / startup):

        store = ModelStore()
        manager = BackgroundTasksManager(store)
        await manager.start()
        ...
        await manager.stop()
    """

    def __init__(self, store: ModelStore) -> None:
        self._store = store
        self._refresh_task: Optional[asyncio.Task] = None
        self._enrich_task: Optional[asyncio.Task] = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        """Start background loops.

        Safe to call once; subsequent calls are ignored.
        """
        if self._refresh_task or self._enrich_task:
            return

        settings = get_settings()
        refresh_interval = settings.refresh_interval_seconds

        async def refresh_loop() -> None:
            logging.info(
                "Background refresh loop started (interval=%ss)",
                refresh_interval,
            )
            # Small initial delay so app can start quickly
            await asyncio.sleep(0.1)
            while not self._stopping.is_set():
                try:
                    models: List[ModelInfo] = await gather_models()
                    await self._store.update_models(models)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logging.error("Error in model refresh loop: %s", e)
                # Wait; wake early if stopping
                try:
                    await asyncio.wait_for(
                        self._stopping.wait(),
                        timeout=refresh_interval,
                    )
                except asyncio.TimeoutError:
                    # normal: timeout means do next refresh
                    pass

            logging.info("Background refresh loop stopped")

        async def enrichment_loop() -> None:
            logging.info("Background enrichment loop started")
            settings_inner = get_settings()
            max_batch = settings_inner.enrichment.max_batch_size

            # Short idle sleep when there's nothing to do
            idle_sleep = 1.0

            while not self._stopping.is_set():
                try:
                    batch = await self._store.get_enrichment_batch(max_batch)
                    if not batch:
                        # Nothing to do right now; nap briefly
                        try:
                            await asyncio.wait_for(
                                self._stopping.wait(), timeout=idle_sleep
                            )
                        except asyncio.TimeoutError:
                            continue
                        continue

                    enriched: List[EnrichedModel] = await enrich_batch(batch)
                    await self._store.apply_enrichment(enriched)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logging.error("Error in enrichment loop: %s", e)
                    # small backoff on error
                    try:
                        await asyncio.wait_for(
                            self._stopping.wait(), timeout=idle_sleep
                        )
                    except asyncio.TimeoutError:
                        continue

            logging.info("Background enrichment loop stopped")

        loop = asyncio.get_running_loop()
        self._refresh_task = loop.create_task(refresh_loop(), name="models-refresh")
        self._enrich_task = loop.create_task(enrichment_loop(), name="models-enrich")

    async def stop(self) -> None:
        """Signal loops to stop and wait for them to exit."""
        if not (self._refresh_task or self._enrich_task):
            return

        self._stopping.set()

        tasks = [t for t in (self._refresh_task, self._enrich_task) if t]
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass

        self._refresh_task = None
        self._enrich_task = None
        self._stopping = asyncio.Event()
