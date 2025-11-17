from __future__ import annotations

from llm_aggregator.models import ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services.enrich_model import enrich_model as enrich_module


def _model(port: int, model_id: str) -> ModelInfo:
    provider = ProviderConfig(
        base_url=f"https://models.example:{port}/v1",
        internal_base_url=f"http://localhost:{port}/v1",
    )
    key = ModelKey(provider=provider, id=model_id)
    return ModelInfo(key=key, raw={"id": model_id})


def test_enrich_batch_maps_brain_response(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '{"enriched":[{"id":"alpha","base_url":"https://models.example:8080/v1","internal_base_url":"http://localhost:8080/v1","summary":"desc","types":["llm"]}]}'

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        models = [_model(8080, "alpha")]

        result = await enrich_module.enrich_batch(models)
        assert len(result) == 1
        assert result[0].key == models[0].key
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
