from __future__ import annotations

import json
from types import SimpleNamespace

from llm_aggregator.models import Model, ProviderConfig, make_model
from llm_aggregator.services.enrich_model import enrich_model as enrich_module
from llm_aggregator.services.enrich_model.enrich_model import _get_enriched_list
from llm_aggregator.services.model_info._sources import get_website_sources


SOURCE_LABEL = get_website_sources()[0].provider_label


def _model(port: int, model_id: str, meta: dict | None = None) -> Model:
    provider_name = f"provider-{port}"
    provider = ProviderConfig(
        base_url=f"https://models.example:{port}/v1",
        internal_base_url=f"http://localhost:{port}/v1",
    )
    payload = {"id": model_id}
    if meta:
        payload["meta"] = meta
    return make_model(provider_name, provider, payload)


def test_enrich_batch_maps_brain_response(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '[{"id":"alpha","provider":"provider-8080","summary":"desc","types":["llm"]}]'

        async def fake_fetch(_model):
            return []

        async def fake_size(_model):
            return None

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)
        models = [_model(8080, "alpha")]

        enriched, failed = await enrich_module.enrich_batch(models)
        assert len(enriched) == 1
        assert failed == []
        assert enriched[0].meta["summary"] == "desc"
        assert enriched[0].meta["base_url"] == "https://models.example:8080/v1"

    import asyncio

    asyncio.run(_run())


def test_enrich_batch_handles_empty_models():
    import asyncio

    assert asyncio.run(enrich_module.enrich_batch([])) == ([], [])


def test_enrich_batch_includes_model_info_messages(monkeypatch):
    async def _run():
        payloads = []

        async def fake_chat(payload):
            payloads.append(payload)
            return '[{"id":"alpha","provider":"provider-8080","summary":"desc","types":["llm"]}]'

        async def fake_fetch(_model):
            snippet = SimpleNamespace(
                source=SimpleNamespace(provider_label=SOURCE_LABEL),
                model_id="alpha",
                markdown="# Title\nSome text",
            )
            return [snippet]

        async def fake_size(_model):
            return None

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)

        models = [_model(8080, "alpha")]
        enriched, failed = await enrich_module.enrich_batch(models)
        assert len(enriched) == 1
        assert failed == []

        messages = payloads[0]["messages"]
        assert messages[2]["content"].startswith(f"Model-Info for alpha from {SOURCE_LABEL}")
        assert messages[-1]["content"].startswith("[")
        assert payloads[0]["temperature"] == enrich_module.get_settings().brain.temperature

    import asyncio
    asyncio.run(_run())


def test_enrich_batch_calls_brain_per_model(monkeypatch):
    async def _run():
        call_count = {"value": 0}

        async def fake_chat(payload):
            call_count["value"] += 1
            data = json.loads(payload["messages"][-1]["content"])
            model_id = data[0]["id"]
            provider_name = data[0]["provider"]
            return json.dumps([{
                "id": model_id,
                "provider": provider_name,
                "summary": f"{model_id}-summary",
                "types": ["llm"],
            }])

        async def fake_fetch(_model):
            return []

        async def fake_size(_model):
            return None

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)

        models = [_model(8080, "alpha"), _model(9090, "beta")]
        enriched, failed = await enrich_module.enrich_batch(models)

        assert {r.id for r in enriched} == {"alpha", "beta"}
        assert call_count["value"] == 2
        assert all("summary" in r.meta for r in enriched)
        assert failed == []

    import asyncio
    asyncio.run(_run())


def test_enrich_batch_stores_files_size_in_meta(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '[{"id": "alpha","provider":"provider-8080","summary": "desc","types": ["llm"]}]'

        async def fake_fetch(_model):
            return []

        async def fake_size(_model):
            return 123

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)

        models = [_model(8080, "alpha")]
        enriched, failed = await enrich_module.enrich_batch(models)

        assert len(enriched) == 1
        assert failed == []
        assert enriched[0].meta["size"] == 123

    import asyncio
    asyncio.run(_run())


def test_enrich_batch_skips_size_gather_when_meta_present(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '[{"id": "alpha","provider":"provider-8080","summary": "desc","types": ["llm"]}]'

        async def fake_fetch(_model):
            return []

        async def fake_size(_model):
            raise AssertionError("size gather should be skipped")

        models = [_model(8080, "alpha", {"size": 321})]

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)

        enriched, failed = await enrich_module.enrich_batch(models)

        assert len(enriched) == 1
        assert failed == []
        assert enriched[0].meta["size"] == 321

    import asyncio
    asyncio.run(_run())


def test_enrich_batch_marks_failed_when_model_missing(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            # provider mismatch -> should be treated as failure
            return '[{"id":"alpha","provider":"wrong","summary":"desc"}]'

        async def fake_fetch(_model):
            return []

        async def fake_size(_model):
            return None

        models = [_model(8080, "alpha")]

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        monkeypatch.setattr(enrich_module, "fetch_model_markdown", fake_fetch)
        monkeypatch.setattr(enrich_module, "gather_files_size", fake_size)

        enriched, failed = await enrich_module.enrich_batch(models)

        assert enriched == []
        assert [m.id for m in failed] == ["alpha"]

    import asyncio
    asyncio.run(_run())


def test_get_enriched_list_handles_invalid_json(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return "not json"

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await _get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())


def test_get_enriched_list_requires_enriched_key(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return '{"data": []}'

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await _get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())


def test_get_enriched_list_catches_unexpected_exceptions(monkeypatch):
    async def _run():
        async def fake_chat(payload):
            return None  # _extract_json_object will raise when calling strip()

        monkeypatch.setattr(enrich_module, "chat_completions", fake_chat)
        assert await _get_enriched_list({}) == []

    import asyncio
    asyncio.run(_run())
