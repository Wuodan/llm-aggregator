from __future__ import annotations

import runpy
import sys

from llm_aggregator import main as main_module


def test_main_invokes_uvicorn(monkeypatch):
    called = {}

    class DummySettings:
        host = "0.0.0.0"
        port = 5555
        log_level = "INFO"
        log_format = "%(message)s"

    def fake_run(app_path, host, port, reload, access_log):
        called["app"] = app_path
        called["host"] = host
        called["port"] = port
        called["reload"] = reload
        called["access_log"] = access_log

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()
    assert called == {
        "app": "llm_aggregator.api:app",
        "host": "0.0.0.0",
        "port": 5555,
        "reload": False,
        "access_log": False,
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
        log_level = "INFO"
        log_format = "%(message)s"

    def fake_run(app_path, host, port, reload, access_log):
        called["app"] = app_path
        called["host"] = host
        called["port"] = port
        called["reload"] = reload
        called["access_log"] = access_log

    fake_uvicorn = type("FakeUvicorn", (), {"run": staticmethod(fake_run)})

    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr("llm_aggregator.config.get_settings", lambda: DummySettings())

    runpy.run_module("llm_aggregator.main", run_name="__main__")
    assert called == {
        "app": "llm_aggregator.api:app",
        "host": "127.0.0.1",
        "port": 4242,
        "reload": False,
        "access_log": False,
    }


def test_main_configures_logging_from_settings(monkeypatch):
    called = {}

    class DummySettings:
        host = "1.2.3.4"
        port = 9999
        log_level = "debug"
        log_format = "%(lineno)d - %(message)s"

    def fake_basic_config(**kwargs):
        called["logging"] = kwargs

    def fake_run(*args, **kwargs):
        called["ran"] = True

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.logging, "basicConfig", fake_basic_config)
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()

    assert called["ran"]
    assert called["logging"]["level"] == "DEBUG"
    assert called["logging"]["format"] == DummySettings.log_format


def test_main_skips_basic_config_when_format_missing(monkeypatch):
    called = {}

    class DummySettings:
        host = "5.6.7.8"
        port = 6000
        log_level = "warning"
        log_format = None

    def fake_basic_config(*args, **kwargs):
        called["basic_config"] = True

    def fake_run(*args, **kwargs):
        called["ran"] = True

    original_set_level = main_module.logging.Logger.setLevel

    def fake_set_level(self, level):
        called["logger_level"] = level
        original_set_level(self, level)

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.logging, "basicConfig", fake_basic_config)
    monkeypatch.setattr(main_module.logging.Logger, "setLevel", fake_set_level)
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()

    assert called["ran"]
    assert called["logger_level"] == "WARNING"
    assert "basic_config" not in called
