from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from llm_aggregator import api as api_module
from llm_aggregator import models as models_module
from llm_aggregator.models import UIConfig
from llm_aggregator.services.stats_collector import stats_history


class DummyStore:
    def __init__(self):
        self.snapshots = 0

    async def get_snapshot(self):
        self.snapshots += 1
        return [
            {
                "id": "m",
                "object": "model",
                "meta": {
                    "size": 42,
                    "base_url": "https://public-provider.example/v1",
                    "summary": "hello",
                },
            }
        ]


class DummyTasksManager:
    def __init__(self):
        self.restarted = False

    async def restart(self):
        self.restarted = True


def test_v1_models_returns_snapshot(monkeypatch):
    store = DummyStore()
    monkeypatch.setattr(api_module, "store", store)

    async def _run():
        response = await api_module.list_models()
        payload = json.loads(response.body.decode())
        assert payload == {
            "object": "list",
            "data": [
                {
                    "id": "m",
                    "object": "model",
                    "meta": {
                        "size": 42,
                        "base_url": "https://public-provider.example/v1",
                        "summary": "hello",
                    },
                }
            ],
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


def _write_ui_bundle(root: Path, *, index_html: str | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    html = index_html or '<div id="apiBaseScript" data-api-base=""></div><script src="/static/main.js"></script>'
    (root / "index.html").write_text(html, encoding="utf-8")
    (root / "main.js").write_text("console.log('bundle');", encoding="utf-8")


def test_build_index_handler_injects_request_base(tmp_path):
    _write_ui_bundle(tmp_path)
    handler = api_module._build_index_handler(
        Path(tmp_path), cache_bust=True, version="test-version"
    )

    async def _run():
        response = await handler(_build_request())
        body = response.body.decode()
        assert 'data-api-base="https://example.com"' in body
        assert 'src="/static/main.js?v=test-version"' in body

    asyncio.run(_run())


def test_build_index_handler_uses_request_host(tmp_path):
    _write_ui_bundle(tmp_path)
    handler = api_module._build_index_handler(
        Path(tmp_path), cache_bust=True, version="test-version"
    )

    async def _run():
        response = await handler(_build_request(host="custom", scheme="http"))
        body = response.body.decode()
        assert 'data-api-base="http://custom"' in body

    asyncio.run(_run())


class DummySettings:
    def __init__(self, ui_config: UIConfig, version: str = "test-version"):
        self.ui = ui_config
        self.version = version


def test_configure_ui_routes_serves_builtin_bundle(tmp_path, monkeypatch):
    _write_ui_bundle(tmp_path)
    monkeypatch.setattr(
        models_module,
        "_default_builtin_static_path",
        lambda: Path(tmp_path),
    )
    ui_config = UIConfig(static_enabled=True)
    app = FastAPI()
    api_module._configure_ui_routes(app, DummySettings(ui_config, version="bundle-version"))

    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'src="/static/main.js?v=bundle-version"' in resp.text

        static_resp = client.get("/static/main.js")
        assert static_resp.status_code == 200
        assert static_resp.text == "console.log('bundle');"
        assert static_resp.headers["Cache-Control"] == "no-cache"


def test_configure_ui_routes_serves_custom_bundle_without_cache_bust(tmp_path, monkeypatch):
    builtin_path = tmp_path / "builtin"
    custom_path = tmp_path / "custom"
    _write_ui_bundle(builtin_path)
    _write_ui_bundle(custom_path)
    monkeypatch.setattr(
        models_module,
        "_default_builtin_static_path",
        lambda: builtin_path,
    )

    ui_config = UIConfig(
        static_enabled=True,
        custom_static_path=custom_path,
    )
    app = FastAPI()
    api_module._configure_ui_routes(app, DummySettings(ui_config, version="custom-version"))

    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'src="/static/main.js?v=custom-version"' not in resp.text
        assert 'src="/static/main.js"' in resp.text

        static_resp = client.get("/static/main.js")
        assert static_resp.status_code == 200
        assert static_resp.headers["Cache-Control"] == "no-cache"


def test_configure_ui_routes_skips_mount_when_disabled(tmp_path, monkeypatch):
    builtin_path = tmp_path / "builtin"
    _write_ui_bundle(builtin_path)
    monkeypatch.setattr(
        models_module,
        "_default_builtin_static_path",
        lambda: builtin_path,
    )

    ui_config = UIConfig(static_enabled=False)
    app = FastAPI()
    api_module._configure_ui_routes(app, DummySettings(ui_config))

    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/static/main.js").status_code == 404


def test_lifespan_starts_and_stops_tasks(monkeypatch):
    events = []

    class DummyTasks:
        @staticmethod
        async def start():
            events.append("start")

        @staticmethod
        async def stop():
            events.append("stop")

    monkeypatch.setattr(api_module, "tasks_manager", DummyTasks())

    async def _run():
        async with api_module.lifespan(api_module.app):
            assert events == ["start"]

    asyncio.run(_run())
    assert events == ["start", "stop"]
