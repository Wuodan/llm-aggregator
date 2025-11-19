from __future__ import annotations

import asyncio
from typing import Dict

from llm_aggregator.models import EnrichedModel, ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services.model_store import ModelStore


def _provider(name: str) -> ProviderConfig:
    return ProviderConfig(base_url=f"https://{name}.example/v1", internal_base_url=f"http://{name}:9000/v1")


def _build_model(provider_name: str, model_id: str, extra: Dict[str, object] | None = None) -> ModelInfo:
    """Helper to build ModelInfo objects with stable ids and providers."""
    provider = _provider(provider_name)
    key = ModelKey(provider=provider, id=model_id)
    raw = {"id": model_id}
    if extra:
        raw.update(extra)
    return ModelInfo(key=key, raw=raw)


def test_model_store_snapshot_and_enrichment_merging():
    async def _run():
        store = ModelStore()
        # Insert models out of order to ensure snapshot sorting logic kicks in.
        gamma = _build_model("provider-b", "Gamma", {"meta": "second"})
        alpha = _build_model("provider-a", "alpha", {"meta": "first"})

        await store.update_models([gamma, alpha])
        assert store.last_update_ts > 0

        # Update existing alpha entry to exercise the "update" branch.
        alpha_updated = _build_model("provider-a", "alpha", {"meta": "updated"})
        await store.update_models([gamma, alpha_updated])

        # Apply enrichment for one model and ensure it survives in the snapshot.
        enriched = EnrichedModel(
            key=gamma.key,
            enriched={"summary": "gamma summary", "types": ["llm"]},
        )
        await store.apply_enrichment([enriched])

        snapshot = await store.get_snapshot()
        assert [entry["llm_aggregator"]["base_url"] for entry in snapshot] == [
            "https://provider-a.example/v1",
            "https://provider-b.example/v1",
        ]
        assert snapshot[1]["llm_aggregator"]["summary"] == "gamma summary"
        assert snapshot[0]["meta"] == "updated"
        aggregator_meta = snapshot[0]["llm_aggregator"]
        assert "id" not in aggregator_meta
        assert "internal_base_url" not in aggregator_meta

    asyncio.run(_run())


def test_model_store_queue_and_requeue_behavior():
    async def _run():
        store = ModelStore()
        model = _build_model("provider-a", "alpha")
        await store.update_models([model])

        batch = await store.get_enrichment_batch(1)
        assert [m.key for m in batch] == [model.key]
        assert await store.get_enrichment_batch(1) == []

        # Requeue succeeds while the model is still present.
        await store.requeue_models(batch)
        batch = await store.get_enrichment_batch(1)
        assert [m.key for m in batch] == [model.key]

        # Removing the model prevents stale batches from being enqueued again.
        await store.update_models([])
        await store.requeue_models(batch)
        assert await store.get_enrichment_batch(1) == []

        # Clearing wipes timestamps and queues.
        await store.clear()
        assert store.last_update_ts == 0

    asyncio.run(_run())


def test_model_store_noop_branches_and_duplicate_queue_guard():
    async def _run():
        store = ModelStore()
        # Guard clauses
        assert await store.get_enrichment_batch(0) == []
        await store.apply_enrichment([])
        await store.requeue_models([])

        # Initial update queues the model once.
        model = _build_model("provider-c", "duplicate")
        await store.update_models([model])

        # Requeuing the same model while it is still in the queue should not create duplicates.
        await store.requeue_models([model])
        batch = await store.get_enrichment_batch(5)
        assert len(batch) == 1

        # Put the model back in the queue and clear the store to ensure queues get drained.
        await store.requeue_models(batch)

        class FlakyQueue:
            def __init__(self):
                self.calls = 0

            def empty(self):
                self.calls += 1
                return self.calls > 1

            def get_nowait(self):
                raise asyncio.QueueEmpty

        store._queue = FlakyQueue()
        await store.clear()
        assert store.last_update_ts == 0
        assert await store.get_enrichment_batch(1) == []

    asyncio.run(_run())
