from __future__ import annotations

import asyncio

from llm_aggregator.models import ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services import model_sources as model_sources_module


def _build_model(port: int, idx: int) -> ModelInfo:
    key = ModelKey(port=port, id=f"model-{idx}")
    return ModelInfo(key=key, raw={"id": key.id, "port": port})


def test_gather_models_combines_and_sorts(monkeypatch):
    async def _run():
        providers = [
            ProviderConfig(base_url="http://provider", port=7001),
            ProviderConfig(base_url="http://provider", port=7000),
        ]

        class DummySettings:
            def __init__(self, provs):
                self.providers = provs

        async def fake_fetch(session, provider):
            # Return models deliberately out of order to ensure gather_models sorts.
            return [
                _build_model(provider.port, 2),
                _build_model(provider.port, 1),
            ]

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: DummySettings(providers))
        monkeypatch.setattr(model_sources_module, "_fetch_models_for_provider", fake_fetch)

        models = await model_sources_module.gather_models()
        assert [m.key.port for m in models] == [7000, 7000, 7001, 7001]
        assert models[0].key.id == "model-1"

    asyncio.run(_run())


def test_gather_models_logs_and_skips_failed_provider(monkeypatch, caplog):
    async def _run():
        providers = [
            ProviderConfig(base_url="http://provider", port=7002),
            ProviderConfig(base_url="http://provider", port=7003),
        ]

        class DummySettings:
            def __init__(self, provs):
                self.providers = provs

        async def fake_fetch(session, provider):
            if provider.port == 7003:
                raise RuntimeError("boom")
            return [_build_model(provider.port, 1)]

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: DummySettings(providers))
        monkeypatch.setattr(model_sources_module, "_fetch_models_for_provider", fake_fetch)

        with caplog.at_level("ERROR"):
            models = await model_sources_module.gather_models()

        assert [m.key.port for m in models] == [7002]
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
        provider = ProviderConfig(base_url="http://host", port=9001)
        payload = {"data": [{"id": "alpha"}, {"id": "beta"}]}
        session = FakeSession(FakeResponse(payload=payload))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())

        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert [m.key.id for m in models] == ["alpha", "beta"]
        assert session.requested[0].endswith("/v1/models")

    asyncio.run(_run())


def test_fetch_models_handles_http_error(monkeypatch):
    async def _run():
        provider = ProviderConfig(base_url="http://host", port=9002)
        session = FakeSession(FakeResponse(status=500, payload={}, text="boom"))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert models == []

    asyncio.run(_run())


def test_fetch_models_handles_non_json_payload(monkeypatch):
    async def _run():
        provider = ProviderConfig(base_url="http://host", port=9003)
        session = FakeSession(FakeResponse(payload=None, text="text body", json_exception=ValueError("bad json")))

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(session, provider)
        assert models == []

    asyncio.run(_run())


def test_fetch_models_handles_transport_failure(monkeypatch):
    async def _run():
        provider = ProviderConfig(base_url="http://host", port=9004)

        class RaisingSession:
            def get(self, url, timeout):
                raise RuntimeError("boom")

        monkeypatch.setattr(model_sources_module, "get_settings", lambda: _settings_with_timeout())
        models = await model_sources_module._fetch_models_for_provider(RaisingSession(), provider)
        assert models == []

    asyncio.run(_run())
