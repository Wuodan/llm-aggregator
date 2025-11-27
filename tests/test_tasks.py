from __future__ import annotations

import asyncio
from types import SimpleNamespace

from llm_aggregator.models import Model, ProviderConfig, make_model
from llm_aggregator.services import tasks as tasks_module


def _model(idx: int) -> Model:
    provider_name = f"provider-{idx}"
    provider = ProviderConfig(
        base_url=f"https://{provider_name}.example/v1",
        internal_base_url=f"http://{provider_name}:8000/v1",
    )
    return make_model(provider_name, provider, {"id": f"model-{idx}"})


class FakeStore:
    def __init__(self):
        self.queue: list[Model] = []
        self.updated = 0
        self.applied = 0
        self.requeued = 0
        self.cleared = 0

    async def update_models(self, models):
        self.updated += 1
        self.queue.extend(models)

    async def get_enrichment_batch(self, max_batch_size: int):
        if not self.queue:
            return []
        batch, self.queue = self.queue[:max_batch_size], self.queue[max_batch_size:]
        return batch

    async def apply_enrichment(self, enriched):
        self.applied += len(enriched)

    async def requeue_models(self, models):
        self.requeued += 1
        self.queue.extend(models)

    async def clear(self):
        self.cleared += 1
        self.queue.clear()


def test_background_tasks_manager_enrichment_flow(monkeypatch):
    async def _run():
        store = FakeStore()
        gather_done = asyncio.Event()
        requeued = asyncio.Event()
        applied = asyncio.Event()

        class DummySettings:
            fetch_models_interval = 0.05
            brain = SimpleNamespace(max_batch_size=2)
            time = SimpleNamespace(enrich_idle_sleep=0)

        models = [_model(1)]
        gather_calls = {"count": 0}

        async def fake_gather_models():
            gather_calls["count"] += 1
            if gather_calls["count"] == 1:
                gather_done.set()
                return list(models)
            return []

        enrich_attempts = {"count": 0}

        async def fake_enrich_batch(batch):
            enrich_attempts["count"] += 1
            if enrich_attempts["count"] == 1:
                requeued.set()
                return []
            enriched = []
            for m in batch:
                m.meta["summary"] = f"{m.id}-summary"
                enriched.append(m)
            applied.set()
            return enriched

        async def fast_sleep_until_stop(stop_event, timeout):
            await asyncio.sleep(0)

        monkeypatch.setattr(tasks_module, "get_settings", lambda: DummySettings())
        monkeypatch.setattr(tasks_module, "gather_models", fake_gather_models)
        monkeypatch.setattr(tasks_module, "enrich_batch", fake_enrich_batch)
        monkeypatch.setattr(tasks_module, "_sleep_until_stop", fast_sleep_until_stop)
        monkeypatch.setattr(tasks_module, "time", SimpleNamespace(sleep=lambda _seconds: None))

        manager = tasks_module.BackgroundTasksManager(store)
        await manager.start()

        await asyncio.wait_for(gather_done.wait(), timeout=1)
        await asyncio.wait_for(requeued.wait(), timeout=1)
        await asyncio.wait_for(applied.wait(), timeout=1)

        assert store.updated >= 1
        assert store.requeued >= 1
        assert store.applied == 1

        await manager.restart()
        assert store.cleared >= 1

        await manager.stop()

    asyncio.run(_run())


def test_sleep_until_stop_wakes_on_timeout():
    async def _run():
        event = asyncio.Event()
        await tasks_module._sleep_until_stop(event, timeout=0)

    asyncio.run(_run())


def test_sleep_until_stop_wakes_when_event_set():
    async def _run():
        event = asyncio.Event()

        async def trigger():
            await asyncio.sleep(0.01)
            event.set()

        asyncio.create_task(trigger())
        await tasks_module._sleep_until_stop(event, timeout=1)

    asyncio.run(_run())
