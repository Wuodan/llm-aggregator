from __future__ import annotations

import textwrap

import pytest

from llm_aggregator import config as config_module
from llm_aggregator import models as models_module
from llm_aggregator.config import CONFIG_ENV_VAR


def test_settings_load_from_custom_yaml(tmp_path, monkeypatch):
    cfg = textwrap.dedent(
        """
        host: "1.2.3.4"
        port: 1234
        brain:
          base_url: "http://brain:8088/v1"
          id: "brain-model"
          api_key: null
          max_batch_size: 2
        time:
          fetch_models_interval: 5
          fetch_models_timeout: 3
          enrich_models_timeout: 7
          enrich_idle_sleep: 1
        providers:
          - base_url: https://public-p1.example/v1
            internal_base_url: http://p1:9000/v1
          - base_url: https://public-p2.example/v1
        model_info_sources:
          - name: "TestSource"
            url_template: "https://source/{model_id}"
        logger_overrides:
          extract2md: warning
          noisy.lib: ERROR
        ui:
          static_enabled: true
          custom_static_path: null
        """
    ).strip()
    path = tmp_path / "test-config.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    config_module._settings = None

    settings = config_module.get_settings()
    assert settings.host == "1.2.3.4"
    assert settings.fetch_models_interval == 5
    assert settings.fetch_models_timeout == 3
    assert settings.enrich_models_timeout == 7
    assert settings.brain.base_url == "http://brain:8088/v1"
    assert settings.brain.id == "brain-model"
    assert settings.brain.api_key is None
    assert settings.log_level == "INFO"
    assert settings.log_format is None
    assert settings.logger_overrides["extract2md"] == "warning"
    assert settings.logger_overrides["noisy.lib"] == "ERROR"
    assert settings.providers[0].base_url == "https://public-p1.example/v1"
    assert settings.providers[0].internal_base_url == "http://p1:9000/v1"
    # Defaults to base_url when not provided
    assert settings.providers[1].base_url == "https://public-p2.example/v1"
    assert settings.providers[1].internal_base_url == "https://public-p2.example/v1"
    assert settings.model_info_sources[0].name == "TestSource"
    assert settings.ui.static_enabled is True
    assert settings.ui.custom_static_path is None

    # Cached object is reused to avoid reparsing.
    assert config_module.get_settings() is settings


def test_missing_config_env_var_raises(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    config_module._settings = None
    try:
        with pytest.raises(RuntimeError):
            config_module.get_settings()
    finally:
        config_module._settings = None


def test_model_info_sources_optional(tmp_path, monkeypatch):
    cfg = textwrap.dedent(
        """
        host: "0.0.0.0"
        port: 1
        brain:
          base_url: "http://brain"
          id: "brain"
        time:
          fetch_models_interval: 1
          fetch_models_timeout: 1
          enrich_models_timeout: 1
          enrich_idle_sleep: 1
        providers:
          - base_url: "http://provider"
        ui:
          static_enabled: false
          custom_static_path: null
        """
    ).strip()
    path = tmp_path / "no-sources.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    config_module._settings = None

    settings = config_module.get_settings()
    try:
        assert settings.model_info_sources == []
    finally:
        config_module._settings = None


def _write_ui_bundle(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text("<html></html>", encoding="utf-8")


def _override_builtin_static_path(monkeypatch, path):
    monkeypatch.setattr(models_module, "_default_builtin_static_path", lambda: path)


def test_invalid_builtin_static_path_raises(tmp_path, monkeypatch):
    cfg = textwrap.dedent(
        """
        host: "0.0.0.0"
        port: 1
        brain:
          base_url: "http://brain"
          id: "brain"
        time:
          fetch_models_interval: 1
          fetch_models_timeout: 1
          enrich_models_timeout: 1
          enrich_idle_sleep: 1
        providers:
          - base_url: "http://provider"
        model_info_sources:
          - name: "Source"
            url_template: "https://example.com/{{model_id}}"
        ui:
          static_enabled: true
          custom_static_path: null
        """
    ).strip()
    path = tmp_path / "bad-ui.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    missing = tmp_path / "missing"
    _override_builtin_static_path(monkeypatch, missing)
    config_module._settings = None

    try:
        with pytest.raises(FileNotFoundError):
            config_module.get_settings()
    finally:
        config_module._settings = None


def test_invalid_custom_static_path_raises(tmp_path, monkeypatch):
    builtin_path = tmp_path / "builtin"
    _write_ui_bundle(builtin_path)

    cfg = textwrap.dedent(
        f"""
        host: "0.0.0.0"
        port: 1
        brain:
          base_url: "http://brain"
          id: "brain"
        time:
          fetch_models_interval: 1
          fetch_models_timeout: 1
          enrich_models_timeout: 1
          enrich_idle_sleep: 1
        providers:
          - base_url: "http://provider"
        model_info_sources:
          - name: "Source"
            url_template: "https://example.com/{{model_id}}"
        ui:
          static_enabled: true
          custom_static_path: "{tmp_path / "custom-missing"}"
        """
    ).strip()
    path = tmp_path / "bad-custom-ui.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    _override_builtin_static_path(monkeypatch, builtin_path)
    config_module._settings = None

    try:
        with pytest.raises(FileNotFoundError):
            config_module.get_settings()
    finally:
        config_module._settings = None


def test_custom_static_path_parses_when_present(tmp_path, monkeypatch):
    builtin_path = tmp_path / "builtin"
    custom_path = tmp_path / "custom"
    _write_ui_bundle(builtin_path)
    _write_ui_bundle(custom_path)

    cfg = textwrap.dedent(
        f"""
        host: "0.0.0.0"
        port: 1
        brain:
          base_url: "http://brain"
          id: "brain"
        time:
          fetch_models_interval: 1
          fetch_models_timeout: 1
          enrich_models_timeout: 1
          enrich_idle_sleep: 1
        providers:
          - base_url: "http://provider"
        model_info_sources:
          - name: "Source"
            url_template: "https://example.com/{{model_id}}"
        ui:
          static_enabled: true
          custom_static_path: "{custom_path}"
        """
    ).strip()
    path = tmp_path / "custom-ui.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    _override_builtin_static_path(monkeypatch, builtin_path)
    config_module._settings = None

    settings = config_module.get_settings()
    try:
        assert settings.ui.builtin_static_path == builtin_path
        assert settings.ui.custom_static_path == custom_path
    finally:
        config_module._settings = None


def test_missing_config_file_raises(monkeypatch):
    monkeypatch.setenv(CONFIG_ENV_VAR, "/tmp/does-not-exist-config.yaml")
    config_module._settings = None
    try:
        with pytest.raises(FileNotFoundError):
            config_module.get_settings()
    finally:
        config_module._settings = None


def test_invalid_model_info_source_template_raises(tmp_path, monkeypatch):
    cfg = textwrap.dedent(
        """
        host: "0.0.0.0"
        port: 1
        brain:
          base_url: "http://brain"
          id: "brain"
        time:
          fetch_models_interval: 1
          fetch_models_timeout: 1
          enrich_models_timeout: 1
          enrich_idle_sleep: 1
        providers:
          - base_url: "http://provider"
        model_info_sources:
          - name: "Broken"
            url_template: "https://example.com/"
        """
    ).strip()
    path = tmp_path / "bad-config.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    config_module._settings = None
    try:
        with pytest.raises(ValueError):
            config_module.get_settings()
    finally:
        config_module._settings = None
