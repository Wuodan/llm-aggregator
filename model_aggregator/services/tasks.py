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
        """Start background loops (idempotent)."""
        if self._refresh_task or self._enrich_task:
            return

        settings = get_settings()
        refresh_interval = float(settings.refresh_interval_seconds)
        idle_sleep = 5.0  # for enrichment loop when queue is empty

        async def refresh_loop() -> None:
            logging.info(
                "Background refresh loop started (interval=%ss)",
                refresh_interval,
            )
            # tiny initial delay so the app is up before first fetch
            await asyncio.sleep(0.1)

            try:
                while not self._stopping.is_set():
                    try:
                        models: List[ModelInfo] = await gather_models()
                        await self._store.update_models(models)
                    except asyncio.CancelledError:
                        # normal during shutdown
                        raise
                    except Exception as e:
                        logging.error("Error in model refresh loop: %r", e)

                    # Sleep in small chunks so we can react quickly to stop()
                    remaining = refresh_interval
                    step = 0.5
                    while remaining > 0 and not self._stopping.is_set():
                        await asyncio.sleep(min(step, remaining))
                        remaining -= step
            except asyncio.CancelledError:
                pass
            finally:
                logging.info("Background refresh loop stopped")

        async def enrichment_loop() -> None:
            logging.info("Background enrichment loop started")
            settings_inner = get_settings()
            max_batch = int(settings_inner.enrichment.max_batch_size)

            try:
                while not self._stopping.is_set():
                    try:
                        batch = await self._store.get_enrichment_batch(max_batch)
                        if not batch:
                            # Nothing to do: short sleep, no errors, just idle.
                            await _sleep_until_stop(self._stopping, idle_sleep)
                            continue

                        enriched: List[EnrichedModel] = await enrich_batch(batch)
                        await self._store.apply_enrichment(enriched)
                    except asyncio.CancelledError:
                        # normal during shutdown
                        raise
                    except Exception as e:
                        logging.error("Error in enrichment loop: %r", e)
                        # brief backoff on real error
                        await _sleep_until_stop(self._stopping, idle_sleep)
            except asyncio.CancelledError:
                pass
            finally:
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
                # expected during shutdown
                pass

        self._refresh_task = None
        self._enrich_task = None
        self._stopping = asyncio.Event()


async def _sleep_until_stop(stop_event: asyncio.Event, timeout: float) -> None:
    """Sleep up to `timeout` seconds, but wake early if stop_event is set.

    No exceptions, no logging: this is normal control flow.
    """
    end = asyncio.get_running_loop().time() + timeout
    step = 0.2
    while not stop_event.is_set():
        now = asyncio.get_running_loop().time()
        if now >= end:
            break
        await asyncio.sleep(min(step, end - now))
