from __future__ import annotations

import asyncio

from llm_aggregator.models import ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services import model_sources as model_sources_module


def _provider(name: str) -> ProviderConfig:
    return ProviderConfig(base_url=f"https://{name}.example/v1", internal_base_url=f"http://{name}:8000/v1")


def _build_model(provider: ProviderConfig, idx: int) -> ModelInfo:
    key = ModelKey(provider=provider, id=f"model-{idx}")
    return ModelInfo(key=key, raw={"id": key.id})


def test_gather_models_combines_and_sorts(monkeypatch):
    async def _run():
        providers = [
            _provider("provider-a"),
            _provider("provider-b"),
        ]

        class DummySettings:
            def __init__(self, provs):
                self.providers = provs

        async def fake_fetch(session, provider):
            return [
                _build_model(provider, 2),
                _build_model(provider, 1),
            ]

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: DummySettings(providers))
        monkeypatch.setattr(model_sources_module, "_fetch_models_for_provider", fake_fetch)

        models = await model_sources_module.gather_models()
        assert [m.key.provider.base_url for m in models] == [
            "https://provider-a.example/v1",
            "https://provider-a.example/v1",
            "https://provider-b.example/v1",
            "https://provider-b.example/v1",
        ]
        assert models[0].key.id == "model-1"

    asyncio.run(_run())


def test_gather_models_logs_and_skips_failed_provider(monkeypatch, caplog):
    async def _run():
        providers = [
            _provider("provider-c"),
            _provider("provider-d"),
        ]

        class DummySettings:
            def __init__(self, provs):
                self.providers = provs

        async def fake_fetch(session, provider):
            if provider.internal_base_url.endswith("provider-d:8000/v1"):
                raise RuntimeError("boom")
            return [_build_model(provider, 1)]

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: DummySettings(providers))
        monkeypatch.setattr(model_sources_module, "_fetch_models_for_provider", fake_fetch)

        with caplog.at_level("ERROR"):
            models = await model_sources_module.gather_models()

        assert [m.key.provider.base_url for m in models] == ["https://provider-c.example/v1"]
        assert any("boom" in rec.message for rec in caplog.records)

    asyncio.run(_run())


class FakeResponse:
    def __init__(self, status=200, payload=None, text="payload", json_exception=None):
        self.status = status
        self._payload = payload
        self._text = text
        self._json_exception = json_exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        if self._json_exception:
            raise self._json_exception
        return self._payload

    async def text(self):
        return self._text


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.requested = None

    def get(self, url, timeout):
        self.requested = (url, timeout)
        return self.response


def _settings_with_timeout(timeout: int = 5):
    class DummySettings:
        fetch_models_timeout = timeout

    return DummySettings()


def test_fetch_models_parses_dict_payload(monkeypatch):
    async def _run():
        provider = _provider("host-a")
        payload = {"data": [{"id": "alpha"}, {"id": "beta"}]}
        session = FakeSession(FakeResponse(payload=payload))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())

        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert [m.key.id for m in models] == ["alpha", "beta"]
        assert session.requested[0].endswith("/v1/models")

    asyncio.run(_run())


def test_fetch_models_handles_http_error(monkeypatch):
    async def _run():
        provider = _provider("host-b")
        session = FakeSession(FakeResponse(status=500, payload={}, text="boom"))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert models == []

    asyncio.run(_run())


def test_fetch_models_handles_non_json_payload(monkeypatch):
    async def _run():
        provider = _provider("host-c")
        session = FakeSession(FakeResponse(payload=None, text="text body", json_exception=ValueError("bad json")))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert models == []

    asyncio.run(_run())


def test_fetch_models_handles_transport_failure(monkeypatch):
    async def _run():
        provider = _provider("host-d")

        class RaisingSession:
            def get(self, url, timeout):
                raise RuntimeError("boom")

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(RaisingSession(), provider)
        assert models == []

    asyncio.run(_run())
