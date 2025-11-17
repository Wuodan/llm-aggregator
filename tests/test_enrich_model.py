from __future__ import annotations

from llm_aggregator.models import ModelInfo, ModelKey
from llm_aggregator.services.enrich_model import enrich_model as enrich_module


def _model(port: int, model_id: str) -> ModelInfo:
    key = ModelKey(port=port, id=model_id)
    return ModelInfo(key=key, raw={"id": model_id, "port": port})


def test_enrich_batch_maps_brain_response(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '{"enriched":[{"id":"alpha","port":8080,"summary":"desc","types":["llm"]}]}'

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        models = [_model(8080, "alpha")]

        result = await enrich_module.enrich_batch(models)
        assert len(result) == 1
        assert result[0].enriched["summary"] == "desc"

    import asyncio

    asyncio.run(_run())


def test_enrich_batch_handles_empty_models():
    import asyncio
    assert asyncio.run(enrich_module.enrich_batch([])) == []


def test_get_enriched_list_handles_invalid_json(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return "not json"

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await enrich_module._get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())


def test_get_enriched_list_requires_enriched_key(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '{"data": []}'

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await enrich_module._get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())


def test_get_enriched_list_catches_unexpected_exceptions(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return None  # _extract_json_object will raise when calling strip()

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await enrich_module._get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())
