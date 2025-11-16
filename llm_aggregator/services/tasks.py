from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from .enrich_model.enrich_model import enrich_batch
from .model_sources import gather_models
from .model_store import ModelStore
from ..config import get_settings
from ..models import ModelInfo, EnrichedModel


class BackgroundTasksManager:
    """Manage background mode-fetch + enrich loops."""

    def __init__(self, store: ModelStore) -> None:
        self._store = store
        self._fetch_models_task: Optional[asyncio.Task] = None
        self._enrich_task: Optional[asyncio.Task] = None
        self._stopping = asyncio.Event()
        self._settings = get_settings()

    async def start(self) -> None:
        """Start background loops (idempotent)."""
        if self._fetch_models_task or self._enrich_task:
            return

        fetch_models_interval = float(self._settings.fetch_models_interval)

        async def refresh_loop() -> None:
            logging.info(
                "Background refresh loop started (interval=%ss)",
                fetch_models_interval,
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
                        pass
                    except Exception as e:
                        logging.error("Error in model refresh loop: %r", e)

                    # Sleep in small chunks so we can react quickly to stop()
                    remaining = fetch_models_interval
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
            max_batch = int(self._settings.brain.max_batch_size)
            idle_sleep = int(self._settings.time.enrich_idle_sleep)

            try:
                while not self._stopping.is_set():
                    try:
                        batch = await self._store.get_enrichment_batch(max_batch)
                        if not batch:
                            await _sleep_until_stop(self._stopping, idle_sleep)
                            continue

                        # Try enrichment; on any failure, requeue the batch.
                        try:
                            enriched: List[EnrichedModel] = await enrich_batch(batch)
                            if enriched:
                                await self._store.apply_enrichment(enriched)
                            else:
                                # brain returned nothing -> requeue to retry later
                                await self._store.requeue_models(batch)
                                time.sleep(5)
                        except Exception as e:
                            logging.error("Brain enrichment failed: %r", e)
                            await self._store.requeue_models(batch)
                            await _sleep_until_stop(self._stopping, idle_sleep)
                            continue

                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logging.error("Error in enrichment loop: %r", e)
                        await _sleep_until_stop(self._stopping, idle_sleep)
            except asyncio.CancelledError:
                pass
            finally:
                logging.info("Background enrichment loop stopped")

        loop = asyncio.get_running_loop()
        self._fetch_models_task = loop.create_task(refresh_loop(), name="models-refresh")
        self._enrich_task = loop.create_task(enrichment_loop(), name="models-enrich")

    async def restart(self) -> None:
        self._fetch_models_task.cancel()
        self._enrich_task.cancel()
        await self._store.clear()
        self._fetch_models_task = None
        self._enrich_task = None
        await self.start()

    async def stop(self) -> None:
        """Signal loops to stop and wait for them to exit."""
        if not (self._fetch_models_task or self._enrich_task):
            return

        self._stopping.set()

        tasks = [t for t in (self._fetch_models_task, self._enrich_task) if t]
        for t in tasks:
            t.cancel()

        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                # expected during shutdown
                pass

        self._fetch_models_task = None
        self._enrich_task = None
        self._stopping = asyncio.Event()


async def _sleep_until_stop(stop_event: asyncio.Event, timeout: int) -> None:
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
