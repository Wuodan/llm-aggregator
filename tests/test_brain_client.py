from __future__ import annotations

import asyncio
from types import SimpleNamespace

from llm_aggregator.services.brain_client import brain_client as brain_module


class FakeResponse:
    def __init__(self, status=200, payload=None, text="", json_exception=None):
        self.status = status
        self._payload = payload
        self._text = text or ""
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
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers, json, timeout):
        self.calls.append((url, headers, json.copy(), timeout))
        return self.response


def _settings(api_key: str | None = "secret"):
    brain = SimpleNamespace(
        host="http://brain-host",
        port=8088,
        id="brain-model",
        api_key=api_key,
    )
    return SimpleNamespace(
        brain=brain,
        enrich_models_timeout=3,
    )


def test_chat_completions_success(monkeypatch):
    payload = {"choices": [{"message": {"content": "ok"}}]}
    session = FakeSession(FakeResponse(status=200, payload=payload))

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: session)

        result = await brain_module.chat_completions({"messages": []})
        assert result == "ok"
        called_url, headers, sent_json, timeout = session.calls[0]
        assert called_url == "http://brain-host:8088/v1/chat/completions"
        assert headers["Authorization"] == "Bearer secret"
        assert sent_json["model"] == "brain-model"
        assert timeout == 3

    asyncio.run(_run())


def test_chat_completions_handles_http_error(monkeypatch):
    session = FakeSession(FakeResponse(status=500, payload={}, text="boom"))

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: session)
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())


def test_chat_completions_handles_exceptions(monkeypatch):
    class RaisingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise TimeoutError("boom")

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings(api_key=None))
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: RaisingSession())
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())


def test_chat_completions_handles_general_exception(monkeypatch):
    class RaisingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: RaisingSession())
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())


def test_chat_completions_handles_non_json_response(monkeypatch):
    response = FakeResponse(payload=None, text="not json", json_exception=ValueError("bad"))
    session = FakeSession(response)

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: session)
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())


def test_chat_completions_validates_response_content(monkeypatch):
    payload = {"choices": [{"message": {"content": "   "}}]}
    session = FakeSession(FakeResponse(status=200, payload=payload))

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings(api_key=None))
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: session)
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())


def test_chat_completions_handles_unexpected_payload(monkeypatch):
    session = FakeSession(FakeResponse(status=200, payload="not-a-dict"))

    async def _run():
        monkeypatch.setattr(brain_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(brain_module.aiohttp, "ClientSession", lambda: session)
        result = await brain_module.chat_completions({"messages": []})
        assert result == ""

    asyncio.run(_run())
