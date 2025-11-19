from __future__ import annotations

import runpy
import sys

from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING_CONFIG

from llm_aggregator import main as main_module


def test_main_invokes_uvicorn(monkeypatch):
    called = {}

    class DummySettings:
        host = "0.0.0.0"
        port = 5555
        log_level = "INFO"
        log_format = "%(message)s"
        logger_overrides = {}

    def fake_run(app_path, **kwargs):
        called["app"] = app_path
        called.update(kwargs)

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()
    assert called["app"] == "llm_aggregator.api:app"
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 5555
    assert called["reload"] is False
    assert called["access_log"] is False
    assert called["log_config"]["loggers"]["uvicorn"]["level"] == "INFO"
    assert (
        called["log_config"]["formatters"]["default"]["fmt"] == DummySettings.log_format
    )


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
        logger_overrides = {}

    def fake_run(app_path, **kwargs):
        called["app"] = app_path
        called.update(kwargs)

    fake_uvicorn = type("FakeUvicorn", (), {"run": staticmethod(fake_run)})

    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr("llm_aggregator.config.get_settings", lambda: DummySettings())

    runpy.run_module("llm_aggregator.main", run_name="__main__")
    assert called["app"] == "llm_aggregator.api:app"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 4242
    assert called["reload"] is False
    assert called["access_log"] is False
    assert "log_config" in called


def test_main_configures_logging_from_settings(monkeypatch):
    called = {}

    class DummySettings:
        host = "1.2.3.4"
        port = 9999
        log_level = "debug"
        log_format = "%(lineno)d - %(message)s"
        logger_overrides = {}

    def fake_basic_config(**kwargs):
        called["logging"] = kwargs

    def fake_run(app_path, **kwargs):
        called["ran"] = True
        called["log_config"] = kwargs["log_config"]

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.logging, "basicConfig", fake_basic_config)
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()

    assert called["ran"]
    assert called["logging"]["level"] == "DEBUG"
    assert called["logging"]["format"] == DummySettings.log_format
    assert (
        called["log_config"]["formatters"]["access"]["fmt"]
        == DummySettings.log_format
    )
    assert called["log_config"]["loggers"]["uvicorn"]["level"] == "DEBUG"


def test_main_skips_basic_config_when_format_missing(monkeypatch):
    called = {}

    class DummySettings:
        host = "5.6.7.8"
        port = 6000
        log_level = "warning"
        log_format = None
        logger_overrides = {}

    def fake_basic_config(*args, **kwargs):
        called["basic_config"] = True

    def fake_run(app_path, **kwargs):
        called["ran"] = True
        called["log_config"] = kwargs["log_config"]

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
    assert (
        called["log_config"]["formatters"]["default"]["fmt"]
        == UVICORN_LOGGING_CONFIG["formatters"]["default"]["fmt"]
    )
    assert called["log_config"]["loggers"]["uvicorn"]["level"] == "WARNING"


def test_main_sets_dependency_logger_levels(monkeypatch):
    called = {}

    class DummySettings:
        host = "9.9.9.9"
        port = 6789
        log_level = "info"
        log_format = None
        logger_overrides = {"extract2md": "WARNING"}

    def fake_basic_config(*args, **kwargs):
        pass

    def fake_run(app_path, **kwargs):
        called["log_config"] = kwargs["log_config"]

    recorded_levels = []

    original_set_level = main_module.logging.Logger.setLevel

    def fake_set_level(self, level):
        recorded_levels.append((self.name, level))
        original_set_level(self, level)

    monkeypatch.setattr(main_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(main_module.logging, "basicConfig", fake_basic_config)
    monkeypatch.setattr(main_module.logging.Logger, "setLevel", fake_set_level)
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()

    loggers = called["log_config"]["loggers"]
    override = loggers["extract2md"]

    assert ("root", "INFO") in recorded_levels
    assert ("extract2md", "WARNING") in recorded_levels
    assert override["level"] == "WARNING"
