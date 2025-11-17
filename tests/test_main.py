from __future__ import annotations

import runpy
import sys

from llm_aggregator import main as main_module


def test_main_invokes_uvicorn(monkeypatch):
    called = {}

    class DummySettings:
        host = "0.0.0.0"
        port = 5555

    def fake_run(app_path, host, port, reload):
        called["app"] = app_path
        called["host"] = host
        called["port"] = port
        called["reload"] = reload

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()
    assert called == {
        "app": "llm_aggregator.api:app",
        "host": "0.0.0.0",
        "port": 5555,
        "reload": False,
    }


def test_dunder_main_delegates_to_main(monkeypatch):
    called = {"count": 0}

    def fake_main():
        called["count"] += 1

    monkeypatch.setattr(main_module, "main", fake_main)
    runpy.run_module("llm_aggregator.__main__", run_name="__main__")
    assert called["count"] == 1


def test_main_module_executes_when_run_directly(monkeypatch):
    called = {}

    class DummySettings:
        host = "127.0.0.1"
        port = 4242

    def fake_run(app_path, host, port, reload):
        called["app"] = app_path
        called["host"] = host
        called["port"] = port
        called["reload"] = reload

    fake_uvicorn = type("FakeUvicorn", (), {"run": staticmethod(fake_run)})

    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr("llm_aggregator.config.get_settings", lambda: DummySettings())

    runpy.run_module("llm_aggregator.main", run_name="__main__")
    assert called == {
        "app": "llm_aggregator.api:app",
        "host": "127.0.0.1",
        "port": 4242,
        "reload": False,
    }
