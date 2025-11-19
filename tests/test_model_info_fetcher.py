from __future__ import annotations

import asyncio

from llm_aggregator.models import ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services.model_info import fetcher as fetcher_module
from llm_aggregator.services.model_info._cache import WebsiteInfoCache
from llm_aggregator.services.model_info._sources import get_website_sources


def _model(model_id: str) -> ModelInfo:
    provider = ProviderConfig(
        base_url="https://provider.example/v1",
        internal_base_url="http://provider.local/v1",
    )
    return ModelInfo(key=ModelKey(provider=provider, id=model_id), raw={"id": model_id})


def test_fetch_model_markdown_fetches_and_caches(monkeypatch):
    async def _run():
        fetcher_module._CACHE = WebsiteInfoCache(ttl_seconds=60)

        calls: dict[str, int] = {}

        async def fake_download(source, model_id):
            calls[source.key] = calls.get(source.key, 0) + 1
            return f"{source.key}-{model_id}"

        monkeypatch.setattr(fetcher_module, "_download_markdown", fake_download)
        sources = get_website_sources()

        first = await fetcher_module.fetch_model_markdown(_model("llama3:8b"))
        assert len(first) == len(sources)
        assert all(s.model_id == "llama3" for s in first)
        assert set(calls.keys()) == {s.key for s in sources}

        second = await fetcher_module.fetch_model_markdown(_model("llama3:8b"))
        assert len(second) == len(sources)
        # Still only one download per source thanks to cache
        assert all(count == 1 for count in calls.values())

    asyncio.run(_run())


def test_fetch_model_markdown_skips_missing_sources(monkeypatch):
    async def _run():
        fetcher_module._CACHE = WebsiteInfoCache(ttl_seconds=60)
        sources = get_website_sources()
        missing_key = sources[0].key

        async def fake_download(source, model_id):
            if source.key == missing_key:
                return None
            return f"{source.key}-{model_id}"

        monkeypatch.setattr(fetcher_module, "_download_markdown", fake_download)

        snippets = await fetcher_module.fetch_model_markdown(_model("qwen"))
        assert len(snippets) == len(sources) - 1
        assert all(snippet.source.key != missing_key for snippet in snippets)

    asyncio.run(_run())
