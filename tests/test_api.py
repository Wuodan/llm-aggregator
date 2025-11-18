from __future__ import annotations

import asyncio
import json
from pathlib import Path

from starlette.requests import Request

from llm_aggregator import api as api_module
from llm_aggregator.services.stats_collector import stats_history


class DummyStore:
    def __init__(self):
        self.snapshots = 0

    async def get_snapshot(self):
        self.snapshots += 1
        return [
            {
                "id": "m",
                "base_url": "https://public-provider.example/v1",
                "internal_base_url": "http://provider:8000/v1",
            }
        ]


class DummyTasksManager:
    def __init__(self):
        self.restarted = False

    async def restart(self):
        self.restarted = True


def test_api_models_returns_snapshot(monkeypatch):
    store = DummyStore()
    monkeypatch.setattr(api_module, "store", store)

    async def _run():
        response = await api_module.api_models()
        payload = json.loads(response.body.decode())
        assert payload == {
            "models": [
                {
                    "id": "m",
                    "base_url": "https://public-provider.example/v1",
                    "internal_base_url": "http://provider:8000/v1",
                }
            ]
        }
        assert store.snapshots == 1

    asyncio.run(_run())


def test_api_stats_reads_history(monkeypatch):
    stats_history.clear()
    stats_history.extend([1, 2, 3])

    response = api_module.get_stats()
    assert json.loads(response.body.decode()) == [1, 2, 3]


def test_clear_data_calls_tasks_manager(monkeypatch):
    tasks = DummyTasksManager()
    monkeypatch.setattr(api_module, "tasks_manager", tasks)

    async def _run():
        response = await api_module.clear_data()
        payload = json.loads(response.body.decode())
        assert payload["status"] == "cleared"
        assert tasks.restarted

    asyncio.run(_run())


def _build_request(host: str = "example.com", scheme: str = "https") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "headers": [(b"host", host.encode())],
        "client": ("127.0.0.1", 12345),
        "scheme": scheme,
        "server": ("testserver", 80),
    }
    return Request(scope)


class DummySettings:
    def __init__(self, api_base_url: str | None):
        self.api_base_url = api_base_url
        self.version = "test-version"


def test_serve_index_injects_request_base(tmp_path, monkeypatch):
    index_html = '<div id="apiBaseScript" data-api-base=""></div><script src="/static/main.js"></script>'
    (tmp_path / "index.html").write_text(index_html, encoding="utf-8")
    monkeypatch.setattr(api_module, "static_dir", Path(tmp_path))
    monkeypatch.setattr(api_module, "settings", DummySettings(api_base_url=None))

    async def _run():
        response = await api_module.serve_index(_build_request())
        body = response.body.decode()
        assert 'data-api-base="https://example.com"' in body
        assert 'src="/static/main.js?v=test-version"' in body

    asyncio.run(_run())


def test_serve_index_prefers_configured_base(tmp_path, monkeypatch):
    index_html = '<div id="apiBaseScript" data-api-base=""></div><script src="/static/main.js"></script>'
    (tmp_path / "index.html").write_text(index_html, encoding="utf-8")
    monkeypatch.setattr(api_module, "static_dir", Path(tmp_path))
    monkeypatch.setattr(api_module, "settings", DummySettings(api_base_url="https://configured"))

    async def _run():
        response = await api_module.serve_index(_build_request(host="other"))
        body = response.body.decode()
        assert 'data-api-base="https://configured"' in body
        assert 'src="/static/main.js?v=test-version"' in body

    asyncio.run(_run())


def test_lifespan_starts_and_stops_tasks(monkeypatch):
    events = []

    class DummyTasks:
        async def start(self):
            events.append("start")

        async def stop(self):
            events.append("stop")

    monkeypatch.setattr(api_module, "tasks_manager", DummyTasks())

    async def _run():
        async with api_module.lifespan(api_module.app):
            assert events == ["start"]

    asyncio.run(_run())
    assert events == ["start", "stop"]
